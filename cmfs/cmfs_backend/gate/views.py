"""
FILE: cmfs/cmfs_backend/gate/views.py
ACTION: CREATE (Phase 8)

Endpoints:
  GET  /api/gate/{unit_id}/delegates/     — full delegate list + attendance state, for offline caching
  POST /api/gate/checkin/                 — mark one delegate attended (online path)
  POST /api/gate/checkin/batch/           — sync an offline attendance queue (deduped)
  POST /api/gate/checkin/cash-payment/    — collect a balance at the gate + check in, atomically (online only)
"""

import logging
import uuid

from django.db import transaction
from django.utils import timezone as dj_tz
from rest_framework.views import APIView
from rest_framework.response import Response

from auth_app.utils import get_client_ip
from auth_app.audit import log as audit_log
from auth_app.permissions import IsAuthenticated, IsGateOfficialOrAbove, user_can_access_unit, user_can_access_county
from conventions.models import ConventionUnit
from delegates.models import Delegate
from payments.models import Payment
from payments.services import confirm_payment

from .models import Attendance
from .serializers import (
    GateDelegateSerializer, SingleCheckinSerializer,
    BatchCheckinRecordSerializer, GateCashPaymentSerializer,
)

logger = logging.getLogger(__name__)


# ── Delegate list (offline cache load) ──────────────────────────────────────────

class GateDelegatesListView(APIView):
    """
    GET /api/gate/{unit_id}/delegates/
    Loaded once into browser memory when a Gate Official logs in (and
    again on any manual refresh); everything a scan needs to resolve
    offline. Only ACTIVE delegates are included — a PENDING delegate has
    no delegate_id yet, so their QR can't exist to be scanned.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        if not IsGateOfficialOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            unit = ConventionUnit.objects.select_related('convention').get(pk=unit_id)
        except ConventionUnit.DoesNotExist:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)

        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        qs = Delegate.objects.filter(convention=unit.convention, registration_status='active').select_related('attendance')
        if unit.scope_type == 'county':
            qs = qs.filter(county=unit.county)
        elif unit.scope_type == 'regional':
            qs = qs.filter(county__region=unit.region)

        return Response({
            'delegates': GateDelegateSerializer(qs, many=True).data,
            'total': qs.count(),
            'synced_at': dj_tz.now().isoformat(),
        })


# ── Single check-in (online path) ───────────────────────────────────────────────

class GateCheckinView(APIView):
    """
    POST /api/gate/checkin/
    body: {"delegate_id": "KER-STU-2026-0042", "timestamp": "..." (optional, defaults to now)}

    Idempotent: scanning an already-checked-in delegate again doesn't
    overwrite the original check-in — it just returns the existing
    record with already_checked_in: true, so a stale local cache never
    clobbers the true first check-in time/officer.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not IsGateOfficialOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = SingleCheckinSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        try:
            delegate = Delegate.objects.get(delegate_id=data['delegate_id'])
        except Delegate.DoesNotExist:
            return Response(
                {'error': 'Delegate not found. Ask for their Delegate ID or registration email.', 'code': 'not_found'},
                status=404,
            )

        if not user_can_access_county(request.auth_user, delegate.county_id):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        user = request.auth_user
        timestamp = data.get('timestamp') or dj_tz.now()

        with transaction.atomic():
            attendance, created = Attendance.objects.select_for_update().get_or_create(delegate=delegate)
            if attendance.checked_in:
                return Response({
                    'already_checked_in': True,
                    'delegate_id': delegate.delegate_id,
                    'checked_in_at': attendance.checked_in_at,
                    'checked_in_by_name': attendance.checked_in_by_name,
                })

            attendance.checked_in = True
            attendance.checked_in_at = timestamp
            attendance.checked_in_by_id = user.id
            attendance.checked_in_by_name = user.full_name
            attendance.save()

        audit_log(
            user=user, action='delegate_checked_in',
            detail=f'Delegate {delegate.delegate_id} checked in at gate',
            ip=get_client_ip(request),
        )

        return Response({
            'already_checked_in': False,
            'delegate_id': delegate.delegate_id,
            'checked_in_at': attendance.checked_in_at,
            'checked_in_by_name': attendance.checked_in_by_name,
        }, status=201)


# ── Batch check-in (offline queue sync) ─────────────────────────────────────────

class GateCheckinBatchView(APIView):
    """
    POST /api/gate/checkin/batch/
    body: {"records": [{"delegate_id": "...", "timestamp": "..."}, ...]}

    Processed one at a time (not all-or-nothing) so a single bad record
    can't block the rest of a reconnecting device's queue. The one JWT on
    this request is the officer credited for every record in the batch —
    each offline scan already carried its own original timestamp, which
    is preserved here rather than replaced with "now".
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not IsGateOfficialOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        records = request.data.get('records')
        if not isinstance(records, list):
            return Response({'error': '"records" must be a list.', 'code': 'validation_error'}, status=400)

        user = request.auth_user
        results = []

        for raw in records:
            serializer = BatchCheckinRecordSerializer(data=raw)
            if not serializer.is_valid():
                results.append({'delegate_id': raw.get('delegate_id'), 'success': False, 'error': 'invalid_record'})
                continue

            data = serializer.validated_data
            delegate_id = data['delegate_id']

            try:
                delegate = Delegate.objects.get(delegate_id=delegate_id)
            except Delegate.DoesNotExist:
                results.append({'delegate_id': delegate_id, 'success': False, 'error': 'not_found'})
                continue

            if not user_can_access_county(user, delegate.county_id):
                results.append({'delegate_id': delegate_id, 'success': False, 'error': 'forbidden'})
                continue

            with transaction.atomic():
                attendance, created = Attendance.objects.select_for_update().get_or_create(delegate=delegate)

                if attendance.checked_in:
                    # Already recorded (either from this same sync retried,
                    # or another device/officer got there first) — never
                    # double-count, just tell the client it's a duplicate.
                    results.append({
                        'delegate_id': delegate_id, 'success': True, 'duplicate': True,
                        'checked_in_at': attendance.checked_in_at, 'checked_in_by_name': attendance.checked_in_by_name,
                    })
                    continue

                attendance.checked_in = True
                attendance.checked_in_at = data['timestamp']
                attendance.checked_in_by_id = user.id
                attendance.checked_in_by_name = user.full_name
                attendance.synced_from_offline = True
                attendance.save()

            audit_log(
                user=user, action='delegate_checked_in_offline_sync',
                detail=f'Delegate {delegate_id} checked in (synced from offline queue, original timestamp {data["timestamp"]})',
                ip=get_client_ip(request),
            )
            results.append({'delegate_id': delegate_id, 'success': True, 'duplicate': False})

        return Response({'results': results})


# ── Cash payment at gate (online only, atomic with check-in) ───────────────────

class GateCashPaymentCheckinView(APIView):
    """
    POST /api/gate/checkin/cash-payment/
    body: {"delegate_id": "...", "amount": "500.00", "notes": "" (optional)}

    Same recording logic as payments.views.CashPaymentView, but wrapped
    in one transaction together with the check-in — a gate official
    collecting an INCOMPLETE-payment delegate's balance always wants both
    to happen together, never a payment recorded with no attendance (or
    vice versa). Blocked entirely offline — there's no queue for this one,
    the frontend must not even show this form without a connection.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not IsGateOfficialOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = GateCashPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        user = request.auth_user

        try:
            delegate = Delegate.objects.select_related('convention', 'county').get(delegate_id=data['delegate_id'])
        except Delegate.DoesNotExist:
            return Response({'error': 'Delegate not found.', 'code': 'not_found'}, status=404)

        if not user_can_access_county(user, delegate.county_id):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        with transaction.atomic():
            payment = Payment.objects.create(
                delegate=delegate,
                amount_paid=data['amount'],
                payment_method='cash',
                status='confirmed',
                entered_by_id=user.id,
                entered_by_name=user.full_name,
                ip_address=get_client_ip(request),
                notes=data.get('notes', ''),
                idempotency_key=uuid.uuid4().hex,
            )
            confirm_payment(payment, amount=data['amount'])
            delegate.refresh_from_db()

            attendance, created = Attendance.objects.select_for_update().get_or_create(delegate=delegate)
            already_checked_in = attendance.checked_in
            if not already_checked_in:
                attendance.checked_in = True
                attendance.checked_in_at = dj_tz.now()
                attendance.checked_in_by_id = user.id
                attendance.checked_in_by_name = user.full_name
            attendance.cash_collected_at_gate = (attendance.cash_collected_at_gate or 0) + data['amount']
            attendance.payment_completed_at_gate = delegate.balance_owed <= 0
            attendance.save()

        audit_log(
            user=user, action='gate_cash_payment',
            detail=f'Gate cash payment KES {data["amount"]} for delegate {delegate.delegate_id}; checked in={not already_checked_in}',
            ip=get_client_ip(request),
        )

        return Response({
            'message': 'Cash payment recorded and delegate checked in.',
            'delegate_id': delegate.delegate_id,
            'payment_status': delegate.payment_status,
            'balance_owed': delegate.balance_owed,
            'checked_in_at': attendance.checked_in_at,
        }, status=201)
