"""
FILE: cmfs/cmfs_backend/delegates/views.py
ACTION: CREATE (Phase 6)

Endpoints:
  GET  /api/delegates/register/options/          — participating counties (public)
  POST /api/delegates/register/                  — public self-registration
  GET  /api/delegates/registration-status/<pk>/   — "Awaiting payment" polling (public)
  POST /api/delegates/manual/                     — Budget Creator manual registration
  GET  /api/delegates/{delegate_id}/              — delegate status page (public, via email link)
  GET  /api/delegates/{delegate_id}/qr/            — direct QR download (public, TEMP fallback — see Phase 7 addendum)
  GET  /api/units/{unit_id}/delegates/            — Budget Creator delegate list
  GET  /api/units/{unit_id}/delegates/summary/    — County Head summary counts
"""

import uuid
import logging

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework.views import APIView
from rest_framework.response import Response
from django_q.tasks import async_task
from django.db import IntegrityError

from auth_app.utils import get_client_ip
from auth_app.permissions import IsAuthenticated, IsFinanceViewerOrAbove, IsBudgetCreatorOrAbove, user_can_access_unit
from auth_app.audit import log as audit_log
from conventions.models import County, ConventionUnit

from .models import Delegate
from .serializers import PublicRegistrationSerializer, ManualRegistrationSerializer, DelegateSerializer
from .utils import resolve_convention_for_county
from payments.models import Payment
from payments.services import confirm_payment

logger = logging.getLogger(__name__)


# ── Registration options (public) ──────────────────────────────────────────────

class RegistrationOptionsView(APIView):
    """GET /api/delegates/register/options/ — counties currently open for registration."""
    permission_classes = []

    def get(self, request):
        units = ConventionUnit.objects.filter(convention__is_registration_open=True).select_related(
            'convention', 'county', 'region'
        )
        counties = set()
        options = []
        for unit in units:
            if unit.scope_type == 'county' and unit.county_id and unit.county_id not in counties:
                counties.add(unit.county_id)
                options.append({
                    'county_id': unit.county.id, 'county_name': unit.county.name,
                    'convention_id': unit.convention.id, 'convention_name': unit.convention.name,
                })
            elif unit.scope_type in ('regional', 'national'):
                region_counties = (
                    County.objects.filter(region_id=unit.region_id) if unit.scope_type == 'regional'
                    else County.objects.all()
                )
                for c in region_counties:
                    if c.id not in counties:
                        counties.add(c.id)
                        options.append({
                            'county_id': c.id, 'county_name': c.name,
                            'convention_id': unit.convention.id, 'convention_name': unit.convention.name,
                        })
        return Response({'options': options})


# ── Public registration ─────────────────────────────────────────────────────────

@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='post')
class PublicRegistrationView(APIView):
    """POST /api/delegates/register/ — no login required."""
    permission_classes = []

    def post(self, request):
        serializer = PublicRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        county = County.objects.get(pk=data['county_id'])
        convention, unit = resolve_convention_for_county(county)
        if not convention:
            return Response(
                {'error': 'Registration is not currently open for this county.', 'code': 'registration_closed'},
                status=400,
            )

        if Delegate.objects.filter(email=data['email'], convention=convention).exists():
            return Response(
                {'error': 'Email already registered for this convention.', 'code': 'duplicate_email'},
                status=400,
            )

        try:
            delegate = Delegate.objects.create(
                full_name=data['full_name'],
                category=data['category'],
                parent_name=data['parent_name'],
                parent_phone=data['parent_phone'],
                email=data['email'],
                county=county,
                convention=convention,
                registration_status='pending',
                registered_by_id=None,
            )
        except IntegrityError:
            # Only the (email, convention) unique_together should ever be hit
            # here in normal operation — re-check it specifically rather than
            # assuming every IntegrityError is a duplicate email. If some
            # other constraint fails, surface it as a real error instead of
            # a misleading "duplicate email" message.
            if Delegate.objects.filter(email=data['email'], convention=convention).exists():
                return Response(
                    {'error': 'Email already registered for this convention.', 'code': 'duplicate_email'},
                    status=400,
                )
            logger.exception('PublicRegistrationView: unexpected IntegrityError creating delegate')
            return Response(
                {'error': 'Registration failed due to a server error. Please try again.', 'code': 'server_error'},
                status=500,
            )

        fee = getattr(convention, {'student': 'fee_student', 'kessat': 'fee_kessat', 'associate': 'fee_associate'}[delegate.category])
        payment = Payment.objects.create(
            delegate=delegate,
            amount_paid=fee,
            payment_method='mpesa',
            status='initiated',
            ip_address=get_client_ip(request),
            idempotency_key=uuid.uuid4().hex, 
        )
        async_task('payments.tasks.initiate_stk_push_task', payment.id)

        audit_log(action='delegate_registered', detail=f'Delegate registered (pending): {delegate.email}', ip=get_client_ip(request))

        return Response({
            'message': 'Registration received. An M-Pesa PIN prompt has been sent to the parent/guardian phone.',
            'registration_id': delegate.id,
            'amount_due': fee,
        }, status=201)


# ── Registration status polling (public "Awaiting payment" page) ──────────────

class RegistrationStatusView(APIView):
    """GET /api/delegates/registration-status/<pk>/ — public, polled after form submit."""
    permission_classes = []

    def get(self, request, pk):
        try:
            delegate = Delegate.objects.get(pk=pk)
        except Delegate.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        latest_payment = delegate.payments.order_by('-timestamp').first()

        # Actively check with Daraja rather than only waiting for the
        # callback — necessary when MPESA_CALLBACK_URL isn't publicly
        # reachable. Cheap no-op once the payment is already resolved.
        if latest_payment and latest_payment.status == 'pending':
            from payments.services import sync_payment_from_daraja
            sync_payment_from_daraja(latest_payment)
            latest_payment.refresh_from_db()
            delegate.refresh_from_db()

        return Response({
            'registration_status': delegate.registration_status,
            'delegate_id': delegate.delegate_id or None,
            'payment_status': latest_payment.status if latest_payment else None,
        })


# ── Manual registration (Budget Creator) ────────────────────────────────────────

class ManualRegistrationView(APIView):
    """POST /api/delegates/manual/ — Budget Creator only."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = ManualRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        county = County.objects.get(pk=data['county_id'])

        user = request.auth_user
        if user.county_id and user.county_id != county.id:
            return Response({'error': 'You can only register delegates for your own county.', 'code': 'forbidden'}, status=403)

        convention, unit = resolve_convention_for_county(county)
        if not convention:
            return Response(
                {'error': 'No open convention covers this county.', 'code': 'registration_closed'}, status=400,
            )

        if Delegate.objects.filter(email=data['email'], convention=convention).exists():
            return Response(
                {'error': 'Email already registered for this convention.', 'code': 'duplicate_email'}, status=400,
            )

        delegate = Delegate.objects.create(
            full_name=data['full_name'],
            category=data['category'],
            parent_name=data['parent_name'],
            parent_phone=data['parent_phone'],
            email=data['email'],
            county=county,
            convention=convention,
            registration_status='pending',
            registered_by_id=user.id,
        )

        amount = data['amount_received_now']

        if data['payment_method'] == 'cash':
            payment = Payment.objects.create(
                delegate=delegate,
                amount_paid=amount,
                payment_method='cash',
                status='confirmed',
                entered_by_id=user.id,
                entered_by_name=user.full_name,
                ip_address=get_client_ip(request),
                idempotency_key=uuid.uuid4().hex,
            )
            confirm_payment(payment, amount=amount)
            delegate.refresh_from_db()
        else:
            payment = Payment.objects.create(
                delegate=delegate,
                amount_paid=amount,
                payment_method='mpesa',
                status='initiated',
                entered_by_id=user.id,
                entered_by_name=user.full_name,
                ip_address=get_client_ip(request),
                idempotency_key=uuid.uuid4().hex,
            )
            async_task('payments.tasks.initiate_stk_push_task', payment.id)

        audit_log(
            user=user, action='delegate_manually_registered',
            detail=f'Delegate {delegate.email} manually registered ({data["payment_method"]})',
            ip=get_client_ip(request),
        )

        return Response({'delegate': DelegateSerializer(delegate).data}, status=201)


# ── Delegate status page (public, via email link) ──────────────────────────────

class DelegateDetailView(APIView):
    """GET /api/delegates/{delegate_id}/ — public status page by Delegate ID."""
    permission_classes = []

    def get(self, request, delegate_id):
        try:
            delegate = Delegate.objects.select_related('convention', 'county').get(delegate_id=delegate_id)
        except Delegate.DoesNotExist:
            return Response({'error': 'Delegate not found.', 'code': 'not_found'}, status=404)

        return Response({'delegate': DelegateSerializer(delegate).data})


# ── Direct QR download — TEMPORARY fallback while Resend isn't configured ───────
#
# PHASE 7 ADDENDUM: the "real" path is delegates.tasks.on_payment_confirmed,
# which queues QR generation + a confirmation email with it attached via
# Django Q2. That requires both a running Q2 cluster (`python manage.py
# qcluster`) and a working RESEND_API_KEY. Neither may be available yet
# (e.g. local dev with no mail provider), so this endpoint generates the QR
# synchronously, on request, bypassing Q2 and Resend entirely, and hands
# back the PNG as a direct download. Delete this view + its URL entry once
# email delivery is confirmed working end-to-end — the QR is already
# emailed automatically and doesn't need a manual download link then.

class DelegateQrCodeView(APIView):
    """
    GET /api/delegates/{delegate_id}/qr/ — public, no auth.
    Generates the QR on the spot if it doesn't exist yet, then serves it
    as a direct download (Content-Disposition: attachment).
    """
    permission_classes = []

    def get(self, request, delegate_id):
        try:
            delegate = Delegate.objects.get(delegate_id=delegate_id)
        except Delegate.DoesNotExist:
            return Response({'error': 'Delegate not found.', 'code': 'not_found'}, status=404)

        if delegate.registration_status != 'active':
            return Response(
                {'error': 'Your QR code will be available once your first payment is confirmed.', 'code': 'not_ready'},
                status=400,
            )

        from .qr import qr_absolute_path, _generate_qr_code_once
        from django.http import FileResponse

        path = qr_absolute_path(delegate)
        if not path.exists():
            if not _generate_qr_code_once(delegate.id):
                return Response(
                    {'error': 'Could not generate the QR code right now. Please try again shortly.', 'code': 'generation_failed'},
                    status=500,
                )

        return FileResponse(
            open(path, 'rb'), as_attachment=True, filename=f'{delegate.delegate_id}.png', content_type='image/png',
        )


# ── Payment reminder (Budget Creator action, Phase 7) ───────────────────────────

class SendPaymentReminderView(APIView):
    """POST /api/delegates/{delegate_id}/send-reminder/ — Budget Creator or above."""
    permission_classes = [IsAuthenticated]

    def post(self, request, delegate_id):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            delegate = Delegate.objects.get(delegate_id=delegate_id)
        except Delegate.DoesNotExist:
            return Response({'error': 'Delegate not found.', 'code': 'not_found'}, status=404)

        if delegate.balance_owed <= 0:
            return Response(
                {'error': 'This delegate has no outstanding balance.', 'code': 'no_balance'}, status=400,
            )

        async_task('delegates.tasks.send_payment_reminder_task', delegate.id)
        audit_log(
            user=request.auth_user, action='payment_reminder_sent',
            detail=f'Payment reminder queued for delegate {delegate.delegate_id}',
            ip=get_client_ip(request),
        )
        return Response({'message': f'Reminder queued for {delegate.full_name}.'})


# ── Staff delegate list / summary ───────────────────────────────────────────────

class UnitDelegatesListView(APIView):
    """GET /api/units/{unit_id}/delegates/ — Budget Creator delegate list with payment status badges."""
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        if not IsFinanceViewerOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            unit = ConventionUnit.objects.select_related('convention').get(pk=unit_id)
        except ConventionUnit.DoesNotExist:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)

        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        qs = Delegate.objects.filter(convention=unit.convention)
        if unit.scope_type == 'county':
            qs = qs.filter(county=unit.county)
        elif unit.scope_type == 'regional':
            qs = qs.filter(county__region=unit.region)

        return Response({'delegates': DelegateSerializer(qs, many=True).data, 'total': qs.count()})


class UnitDelegatesSummaryView(APIView):
    """GET /api/units/{unit_id}/delegates/summary/ — County Head summary counts."""
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        if not IsFinanceViewerOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            unit = ConventionUnit.objects.select_related('convention').get(pk=unit_id)
        except ConventionUnit.DoesNotExist:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)

        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        qs = Delegate.objects.filter(convention=unit.convention)
        if unit.scope_type == 'county':
            qs = qs.filter(county=unit.county)
        elif unit.scope_type == 'regional':
            qs = qs.filter(county__region=unit.region)

        counts = {'COMPLETE': 0, 'INCOMPLETE': 0, 'NOT_PAID': 0, 'PENDING': 0, 'OVERPAID': 0}
        for delegate in qs:
            counts[delegate.payment_status] = counts.get(delegate.payment_status, 0) + 1

        return Response({'unit_id': unit.id, 'total_delegates': qs.count(), 'counts': counts})