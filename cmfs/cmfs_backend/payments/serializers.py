"""
FILE: cmfs/cmfs_backend/payments/serializers.py
ACTION: CREATE (Phase 6)
"""

from decimal import Decimal
from rest_framework import serializers
from .models import Payment


class CashPaymentSerializer(serializers.Serializer):
    """POST /api/payments/cash/ — Budget Creator only."""
    delegate = serializers.IntegerField()  # internal Delegate pk
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class MpesaInitiateSerializer(serializers.Serializer):
    """POST /api/payments/mpesa/initiate/ — retry or continue a payment for an existing delegate."""
    delegate = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'delegate_id', 'amount_paid', 'payment_method',
            'mpesa_transaction_id', 'status', 'entered_by_id', 'entered_by_name',
            'timestamp', 'notes',
        ]