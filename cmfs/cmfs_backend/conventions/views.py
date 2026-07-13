"""
FILE: cmfs/cmfs_backend/conventions/views.py
ACTION: CREATE (Phase 3)

Endpoints:
  GET    /api/conventions/              — list
  POST   /api/conventions/             — create (Super Admin)
  GET    /api/conventions/<id>/         — detail
  PATCH  /api/conventions/<id>/         — update (DRAFT only)
  POST   /api/conventions/<id>/publish/ — DRAFT → OPEN (locks scope)
  POST   /api/conventions/<id>/activate/ — OPEN → ACTIVE
  POST   /api/conventions/<id>/end/    — ACTIVE → ENDED
  POST   /api/conventions/<id>/close/  — ENDED → FINANCIALLY_CLOSED (TOTP required)
  POST   /api/conventions/<id>/archive/ — FINANCIALLY_CLOSED → ARCHIVED
  GET    /api/conventions/counties/    — list counties (for wizard dropdown)
  GET    /api/conventions/regions/     — list regions
  POST   /api/conventions/<id>/opening-day-reports/ — trigger opening day report generation
"""

from django.utils import timezone as dj_tz
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from django_q.tasks import async_task

from auth_app.utils import verify_totp_code, get_client_ip
from auth_app.audit import log as audit_log
from auth_app.permissions import IsAuthenticated, IsSuperAdmin, user_can_access_unit

from .models import Convention, ConventionUnit, County, Region
from .serializers import (
    ConventionListSerializer,
    ConventionDetailSerializer,
    ConventionCreateSerializer,
    ConventionUpdateSerializer,
    ConventionTransitionSerializer,
    CountySerializer,
    RegionSerializer,
)
from .permissions import user_can_view_convention, user_can_manage_convention
from . import tasks


HEAD_ROLES = {'super_admin', 'national_head', 'regional_head', 'county_head'}
MANAGEMENT_ROLES = {'super_admin'}


def _scope_lock_convention(convention, user):
    """Permanently lock scope, fees, and unit structure. Called on DRAFT → OPEN."""
    convention.scope_locked = True
    convention.scope_locked_at = dj_tz.now()
    convention.is_registration_open = True
    convention.status = Convention.STATUS_OPEN
    convention.published_at = dj_tz.now()


# ── Convention List / Create ───────────────────────────────────────────────────

class ConventionListCreateView(APIView):
    """
    GET  /api/conventions/  — list conventions (role-scoped)
    POST /api/conventions/  — create convention (Super Admin only)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.auth_user
        qs = Convention.objects.prefetch_related('units').order_by('-created_at')#"for every Convention you fetch, also go fetch all the ConventionUnit rows that belong to it, in a single extra query, and cache them

        # Scope filtering
        if user.role == 'super_admin':
            pass  # all
        elif user.role == 'national_head':
            qs = qs.filter(scope='national')
        elif user.role == 'regional_head':
            qs = qs.filter(units__region_id=user.region_id).distinct()
        elif user.role == 'county_head':
            qs = qs.filter(units__county_id=user.county_id).distinct()
        elif user.role in ('budget_creator', 'finance_viewer', 'gate_official'):
            # These roles exist at county, regional, and national level and
            # inherit their scope from whoever invited them — check whichever
            # id they actually carry rather than assuming county_id.
            if user.county_id:
                qs = qs.filter(units__county_id=user.county_id).distinct()
            elif user.region_id:
                qs = qs.filter(units__region_id=user.region_id).distinct()
            else:
                qs = qs.filter(scope='national').distinct()
        else:
            # delegates and others see nothing here
            return Response({'conventions': [], 'total': 0})

        # Non-Super-Admin roles never see DRAFT conventions — only once a
        # convention has been published (OPEN) or moved further along its
        # lifecycle. DRAFT conventions are still being configured and should
        # remain visible to Super Admin only.
        if user.role != 'super_admin':
            qs = qs.exclude(status=Convention.STATUS_DRAFT)

        # Optional status filter
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        total = qs.count()
        serializer = ConventionListSerializer(qs, many=True)
        return Response({'conventions': serializer.data, 'total': total})

    def post(self, request):
        user = request.auth_user
        if user.role != 'super_admin':
            return Response({'error': 'Only Super Admin can create conventions.', 'code': 'forbidden'}, status=403)

        serializer = ConventionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        ip = get_client_ip(request)

        convention = Convention.objects.create(
            name=data['name'],
            scope=data['scope'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            description=data.get('description', ''),
            fee_student=data['fee_student'],
            fee_kessat=data['fee_kessat'],
            fee_associate=data['fee_associate'],
            status=Convention.STATUS_DRAFT,
            created_by_id=user.id,
        )

        # Create convention units
        units_data = data.get('units', [])
        for u in units_data:
            scope_id = u.get('scope_id')
            county = None
            region = None
            if data['scope'] == 'county' and scope_id:
                try:
                    county = County.objects.get(pk=scope_id)
                except County.DoesNotExist:
                    pass
            elif data['scope'] == 'regional' and scope_id:
                try:
                    region = Region.objects.get(pk=scope_id)
                except Region.DoesNotExist:
                    pass

            ConventionUnit.objects.create(
                convention=convention,
                scope_type=data['scope'],
                scope_id=scope_id,
                county=county,
                region=region,
            )

        audit_log(
            user=user,
            action='convention_created',
            detail=f'Convention "{convention.name}" (scope={convention.scope}) created',
            ip=ip,
        )

        detail_serializer = ConventionDetailSerializer(convention)
        return Response({'convention': detail_serializer.data}, status=201)


# ── Convention Detail / Update ─────────────────────────────────────────────────

class ConventionDetailView(APIView):
    """
    GET   /api/conventions/<id>/  — detail (role-scoped read)
    PATCH /api/conventions/<id>/  — update (DRAFT only, management roles)
    """
    permission_classes = [IsAuthenticated]

    def _get_convention_or_404(self, pk):
        try:
            return Convention.objects.prefetch_related('units__county', 'units__region').get(pk=pk)
        except Convention.DoesNotExist:
            return None

    def get(self, request, pk):
        convention = self._get_convention_or_404(pk)
        if not convention:
            return Response({'error': 'Convention not found.', 'code': 'not_found'}, status=404)

        if not user_can_view_convention(request.auth_user, convention):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = ConventionDetailSerializer(convention)
        return Response({'convention': serializer.data})

    def patch(self, request, pk):
        convention = self._get_convention_or_404(pk)
        if not convention:
            return Response({'error': 'Convention not found.', 'code': 'not_found'}, status=404)

        user = request.auth_user
        if not user_can_manage_convention(user, convention):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        if not convention.is_editable:
            return Response(
                {'error': 'Convention can only be edited in DRAFT status.', 'code': 'not_editable'},
                status=400,
            )

        serializer = ConventionUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        for field, value in data.items():
            setattr(convention, field, value)
        convention.save()

        audit_log(
            user=user,
            action='convention_updated',
            detail=f'Convention id={convention.id} updated fields: {list(data.keys())}',
            ip=get_client_ip(request),
        )

        return Response({'convention': ConventionDetailSerializer(convention).data})


# ── Lifecycle Transitions ──────────────────────────────────────────────────────

class ConventionPublishView(APIView):
    """
    POST /api/conventions/<id>/publish/
    DRAFT → OPEN
    Permanently locks scope, fees, and unit structure.
    Super Admin only. Shows confirmation warning on frontend before calling.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.auth_user
        if user.role != 'super_admin':
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            convention = Convention.objects.get(pk=pk)
        except Convention.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if convention.status != Convention.STATUS_DRAFT:
            return Response(
                {'error': f'Convention is already {convention.status}. Can only publish from DRAFT.'},
                status=400,
            )

        _scope_lock_convention(convention, user)
        convention.save()

        audit_log(
            user=user,
            action='convention_published',
            detail=f'Convention "{convention.name}" published (scope locked)',
            ip=get_client_ip(request),
        )

        # Queue background task: send invitation emails to all assigned heads
        async_task('conventions.tasks.send_convention_published_notifications', convention.id)

        return Response({
            'message': f'Convention "{convention.name}" is now OPEN. Scope and fees are permanently locked.',
            'convention': ConventionDetailSerializer(convention).data,
        })


class ConventionActivateView(APIView):
    """
    POST /api/conventions/<id>/activate/
    OPEN (or DRAFT) → ACTIVE
    Can be triggered manually or is auto-triggered by daily cron on start_date.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.auth_user
        if user.role not in ('super_admin', 'national_head', 'regional_head', 'county_head'):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            convention = Convention.objects.get(pk=pk)
        except Convention.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if convention.status != Convention.STATUS_OPEN:
            return Response(
                {'error': 'Convention must be published (OPEN) before activating.', 'code': 'not_published'},
                status=400,
            )

        if not user_can_manage_convention(user, convention):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        convention.status = Convention.STATUS_ACTIVE
        convention.started_at = dj_tz.now()
        convention.save()

        audit_log(
            user=user,
            action='convention_activated',
            detail=f'Convention "{convention.name}" set to ACTIVE',
            ip=get_client_ip(request),
        )

        async_task('conventions.tasks.send_convention_started_notification', convention.id)

        return Response({
            'message': f'Convention "{convention.name}" is now ACTIVE. Gate module enabled.',
            'convention': ConventionDetailSerializer(convention).data,
        })


class ConventionEndView(APIView):
    """
    POST /api/conventions/<id>/end/
    ACTIVE → ENDED
    Can be triggered manually or auto-triggered by daily cron on end_date.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.auth_user
        if user.role not in ('super_admin', 'national_head', 'regional_head', 'county_head'):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            convention = Convention.objects.get(pk=pk)
        except Convention.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if convention.status != Convention.STATUS_ACTIVE:
            return Response(
                {'error': f'Convention must be ACTIVE to end. Current: {convention.status}.'},
                status=400,
            )

        if not user_can_manage_convention(user, convention):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        convention.status = Convention.STATUS_ENDED
        convention.ended_at = dj_tz.now()
        convention.is_registration_open = False
        convention.save()

        audit_log(
            user=user,
            action='convention_ended',
            detail=f'Convention "{convention.name}" ended',
            ip=get_client_ip(request),
        )

        async_task('conventions.tasks.send_convention_ended_notification', convention.id)

        return Response({
            'message': f'Convention "{convention.name}" has ENDED. Registration closed, gate deactivated.',
            'convention': ConventionDetailSerializer(convention).data,
        })


class ConventionCloseView(APIView):
    """
    POST /api/conventions/<id>/close/
    ENDED → FINANCIALLY_CLOSED
    Requires TOTP confirmation from the head. Irreversible.
    Pre-close checklist validation is done on the frontend; this endpoint just
    validates the TOTP and transitions.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.auth_user
        if user.role not in ('super_admin', 'national_head'):
            return Response({'error': 'Financial close is restricted to Super Admin and National Head.', 'code': 'forbidden'}, status=403)

        try:
            convention = Convention.objects.get(pk=pk)
        except Convention.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if convention.status != Convention.STATUS_ENDED:
            return Response(
                {'error': f'Convention must be ENDED to close financially. Current: {convention.status}.'},
                status=400,
            )

        # Note: unlike other transitions, National Head can close ANY
        # convention here (not just national-scope ones) — financial close
        # locks the entire convention across every ConventionUnit, so
        # user_can_manage_convention's scope-matching doesn't apply.

        # TOTP verification required
        totp_code = request.data.get('totp_code', '').strip()
        if not totp_code:
            return Response({'error': 'TOTP code is required for financial close.', 'code': 'totp_required'}, status=400)

        if not user.totp_enabled or not user.totp_secret:
            return Response({'error': 'Your account does not have TOTP enabled.', 'code': 'totp_not_enabled'}, status=403)

        if not verify_totp_code(user.totp_secret, totp_code):
            return Response({'error': 'Invalid TOTP code.', 'code': 'invalid_totp'}, status=403)

        convention.status = Convention.STATUS_FINANCIALLY_CLOSED
        convention.financially_closed_at = dj_tz.now()
        convention.financially_closed_by_id = user.id
        convention.save()

        audit_log(
            user=user,
            action='convention_financially_closed',
            detail=f'Convention "{convention.name}" financially closed',
            ip=get_client_ip(request),
        )

        # Generates final reports synchronously (so they're downloadable
        # immediately), then queues one background email task per
        # recipient — each with only the report file(s) they're entitled
        # to see attached (Super Admin gets everything; each head/finance
        # viewer gets only their own unit's reports).
        tasks.generate_final_reports(convention.id, triggered_by=user.id)

        return Response({
            'message': f'Convention "{convention.name}" is now FINANCIALLY CLOSED. '
                       f'Final reports have been generated and are being emailed to all heads.',
            'convention': ConventionDetailSerializer(convention).data,
        })


class ConventionArchiveView(APIView):
    """
    POST /api/conventions/<id>/archive/
    FINANCIALLY_CLOSED → ARCHIVED
    Super Admin only.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.auth_user
        if user.role != 'super_admin':
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            convention = Convention.objects.get(pk=pk)
        except Convention.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if convention.status != Convention.STATUS_FINANCIALLY_CLOSED:
            return Response(
                {'error': f'Convention must be FINANCIALLY_CLOSED to archive. Current: {convention.status}.'},
                status=400,
            )

        convention.status = Convention.STATUS_ARCHIVED
        convention.archived_at = dj_tz.now()
        convention.save()

        audit_log(
            user=user,
            action='convention_archived',
            detail=f'Convention "{convention.name}" archived',
            ip=get_client_ip(request),
        )

        return Response({'message': f'Convention "{convention.name}" has been archived.'})


# ── Opening Day Reports ────────────────────────────────────────────────────────

class ConventionOpeningDayReportsView(APIView):
    """
    POST /api/conventions/<id>/opening-day-reports/
    Triggers generation and email distribution of opening day reports.
    Available to Super Admin and Head roles from ACTIVE status onwards.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.auth_user
        if user.role not in HEAD_ROLES:
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            convention = Convention.objects.get(pk=pk)
        except Convention.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if convention.status not in (Convention.STATUS_ACTIVE, Convention.STATUS_ENDED):
            return Response(
                {'error': 'Opening day reports are only available during or after ACTIVE status.'},
                status=400,
            )

        if not user_can_view_convention(user, convention):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        tasks.generate_opening_day_reports(convention.id, triggered_by=user.id)

        audit_log(
            user=user,
            action='opening_day_reports_triggered',
            detail=f'Opening day reports requested for convention id={convention.id}',
            ip=get_client_ip(request),
        )

        return Response({'message': 'Opening day reports are being generated and will be emailed shortly.'})


# ── Geography endpoints (for wizard dropdowns) ─────────────────────────────────

class CountyListView(APIView):
    """
    GET /api/conventions/counties/ — all counties with region info.
    Open to any authenticated role (not just heads): budget_creator,
    finance_viewer, and gate_official also need this — e.g. a region-scoped
    budget_creator must pick which county within their region a manually
    registered delegate belongs to. This is non-sensitive static geography
    data (county names), already exposed unauthenticated via the delegate
    self-registration options endpoint, so widening this is safe.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        counties = County.objects.select_related('region').order_by('name')
        serializer = CountySerializer(counties, many=True)
        return Response({'counties': serializer.data})


class RegionListView(APIView):
    """GET /api/conventions/regions/ — all regions. Open to any authenticated role (see CountyListView)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        regions = Region.objects.order_by('name')
        serializer = RegionSerializer(regions, many=True)
        return Response({'regions': serializer.data})
    

class MyUnitsView(APIView):
    """
    GET /api/my-units/
    Resolves the caller's applicable ConventionUnit(s) across currently
    open-or-later conventions (i.e. everything except DRAFT) matching their
    county_id/region_id, or national scope. Empty list is valid — it means
    no live convention covers this user's geography yet.
    Membership is computed per-request; nothing is stored on the user.
    """
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        user = request.auth_user
        units = (
            ConventionUnit.objects
            .select_related('convention', 'county', 'region')
            .exclude(convention__status=Convention.STATUS_DRAFT)
        )
 
        results = []
        for unit in units:
            if user_can_access_unit(user, unit):
                results.append({
                    'convention_id': unit.convention_id,
                    'convention_name': unit.convention.name,
                    'status': unit.convention.status,
                    'unit_id': unit.id,
                    'scope_type': unit.scope_type,
                    'display_name': unit.display_name,
                })
 
        return Response(results)