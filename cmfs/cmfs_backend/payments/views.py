"""
FILE: cmfs/cmfs_backend/payments/views.py
ACTION: CREATE (Phase 6)

Endpoints:
  POST /api/payments/mpesa/initiate/    — (re)trigger STK push for a delegate
  POST /api/payments/mpesa/callback/    — Safaricom webhook (IP-whitelisted + HMAC)
  POST /api/payments/cash/              — Budget Creator records a cash payment
  GET  /api/delegates/{delegate_id}/payments/
"""

import uuid
import json
import logging

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework.views import APIView
from rest_framework.response import Response
from django_q.tasks import async_task

from auth_app.utils import get_client_ip
from auth_app.permissions import IsAuthenticated, IsBudgetCreatorOrAbove, user_can_access_county
from cmfs_backend.utils.ratelimit import user_or_ip_key
from delegates.models import Delegate

from .models import Payment
from .serializers import CashPaymentSerializer, MpesaInitiateSerializer, PaymentSerializer
from .hmac_utils import verify_callback_hmac
from .services import confirm_payment, fail_payment

logger = logging.getLogger(__name__)


# ── M-Pesa initiate ──────────────────────────────────────────────────────────────

@method_decorator(ratelimit(key=user_or_ip_key, rate='20/m', method='POST', block=True), name='post')
class MpesaInitiateView(APIView):
    """
    POST /api/payments/mpesa/initiate/
    Creates a new 'initiated' Payment and queues the STK push.

    Dual use, both covered by the same 20/min (per user, or per IP when
    unauthenticated) rate limit:
      - Public + unauthenticated: retrying the *first* payment for a
        delegate whose registration is still PENDING (e.g. the original
        STK prompt timed out or was dismissed).
      - Authenticated (Budget Creator or above): collecting an
        installment payment for a delegate already ACTIVE in their
        scope.
    """
    permission_classes = []

    def post(self, request):
        serializer = MpesaInitiateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        try:
            delegate = Delegate.objects.select_related('convention', 'county').get(pk=data['delegate'])
        except Delegate.DoesNotExist:
            return Response({'error': 'Delegate not found.', 'code': 'not_found'}, status=404)

        auth_user = getattr(request, 'auth_user', None)

        if auth_user is None:
            # Public retry — only while no payment has ever been confirmed yet.
            if delegate.registration_status != 'pending':
                return Response({
                    'error': 'This delegate is already registered. Please see your County Budget '
                             'Creator to pay any remaining balance.',
                    'code': 'forbidden',
                }, status=403)
        else:
            if not IsBudgetCreatorOrAbove().has_permission(request, self):
                return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)
            if not user_can_access_county(auth_user, delegate.county_id):
                return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        payment = Payment.objects.create(
            delegate=delegate,
            amount_paid=data['amount'],
            payment_method='mpesa',
            status='initiated',
            ip_address=get_client_ip(request),
            idempotency_key=uuid.uuid4().hex,
        )
        async_task('payments.tasks.initiate_stk_push_task', payment.id)

        return Response({
            'message': 'STK Push queued. Ask the parent/guardian to check their phone for the M-Pesa PIN prompt.',
            'payment': PaymentSerializer(payment).data,
        }, status=201)


# ── M-Pesa callback ───────────────────────────────────────────────────────────────

class MpesaCallbackView(APIView):
    """
    POST /api/payments/mpesa/callback/
    Public Safaricom webhook. IP whitelist enforced in
    payments.middleware.MpesaIPWhitelistMiddleware (runs before this view).
    HMAC verified here as the required second layer (Security Section 9).
    Always acknowledges HTTP 200 immediately per Daraja's requirements —
    processing itself is fast/synchronous here since it's just a status
    update, no external calls are made in this handler.
    """
    permission_classes = []  # public — protected by IP whitelist + HMAC, not JWT

    def post(self, request):
        if not verify_callback_hmac(request):
            logger.warning('MpesaCallbackView: HMAC verification failed')
            return Response({'error': 'Invalid signature.', 'code': 'forbidden'}, status=403)

        try:
            body = json.loads(request.body or b'{}')
        except json.JSONDecodeError:
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'}, status=200)

        stk_callback = (body.get('Body') or {}).get('stkCallback') or {}
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')

        if not checkout_request_id:
            logger.warning('MpesaCallbackView: no CheckoutRequestID in callback body')
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'}, status=200)

        try:
            payment = Payment.objects.select_related('delegate').get(idempotency_key=checkout_request_id)
        except Payment.DoesNotExist:
            logger.warning(f'MpesaCallbackView: no payment found for CheckoutRequestID={checkout_request_id}')
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'}, status=200)

        # Idempotency: a payment already resolved (confirmed/failed/timeout)
        # is never reprocessed, no matter how many times Safaricom retries —
        # EXCEPT a payment confirmed earlier via the STK Query fallback
        # (no callback ever reached us) is still missing its receipt
        # number, so a genuine success callback backfills that one field.
        if payment.status in ('confirmed', 'failed', 'timeout'):
            if payment.status == 'confirmed' and not payment.mpesa_transaction_id and result_code == 0:
                items = {
                    item.get('Name'): item.get('Value')
                    for item in (stk_callback.get('CallbackMetadata') or {}).get('Item', [])
                }
                receipt = items.get('MpesaReceiptNumber')
                if receipt and not Payment.objects.filter(mpesa_transaction_id=receipt).exclude(pk=payment.id).exists():
                    payment.mpesa_transaction_id = receipt
                    payment.save()
                    logger.info(f'MpesaCallbackView: backfilled receipt {receipt} onto payment {payment.id}')
            else:
                logger.info(f'MpesaCallbackView: payment {payment.id} already {payment.status}, ignoring duplicate callback')
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'}, status=200)

        if result_code == 0:
            items = {
                item.get('Name'): item.get('Value')
                for item in (stk_callback.get('CallbackMetadata') or {}).get('Item', [])
            }
            amount = items.get('Amount', payment.amount_paid)
            receipt = items.get('MpesaReceiptNumber')

            if receipt and Payment.objects.filter(mpesa_transaction_id=receipt).exclude(pk=payment.id).exists():
                logger.warning(f'MpesaCallbackView: duplicate MpesaReceiptNumber={receipt}, ignoring')
                return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'}, status=200)

            confirm_payment(payment, amount=amount, mpesa_transaction_id=receipt)
        else:
            fail_payment(payment, reason=stk_callback.get('ResultDesc', 'Payment failed or cancelled'), result_code=str(result_code))

        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'}, status=200)


# ── Cash payments ────────────────────────────────────────────────────────────────

@method_decorator(ratelimit(key=user_or_ip_key, rate='30/m', method='POST', block=True), name='post')
class CashPaymentView(APIView):
    """
    POST /api/payments/cash/  — Budget Creator only.
    Confirms immediately (no callback to wait for). If this is the
    delegate's first confirmed payment, activates them + generates their
    Delegate ID.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = CashPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        try:
            delegate = Delegate.objects.select_related('convention', 'county').get(pk=data['delegate'])
        except Delegate.DoesNotExist:
            return Response({'error': 'Delegate not found.', 'code': 'not_found'}, status=404)

        if not user_can_access_county(request.auth_user, delegate.county_id):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        payment = Payment.objects.create(
            delegate=delegate,
            amount_paid=data['amount'],
            payment_method='cash',
            status='confirmed',
            entered_by_id=request.auth_user.id,
            entered_by_name=request.auth_user.full_name,
            ip_address=get_client_ip(request),
            notes=data.get('notes', ''),
            idempotency_key=uuid.uuid4().hex,
        )
        confirm_payment(payment, amount=data['amount'])

        delegate.refresh_from_db()
        return Response({
            'message': 'Cash payment recorded.',
            'delegate': {
                'id': delegate.id,
                'delegate_id': delegate.delegate_id,
                'payment_status': delegate.payment_status,
                'balance_owed': delegate.balance_owed,
            },
            'payment': PaymentSerializer(payment).data,
        }, status=201)


# ── Delegate payment history ───────────────────────────────────────────────────

class DelegatePaymentsListView(APIView):
    """GET /api/delegates/{delegate_id}/payments/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, delegate_id):
        try:
            delegate = Delegate.objects.get(delegate_id=delegate_id)
        except Delegate.DoesNotExist:
            return Response({'error': 'Delegate not found.', 'code': 'not_found'}, status=404)

        if not user_can_access_county(request.auth_user, delegate.county_id):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        payments = delegate.payments.all()
        return Response({'payments': PaymentSerializer(payments, many=True).data})