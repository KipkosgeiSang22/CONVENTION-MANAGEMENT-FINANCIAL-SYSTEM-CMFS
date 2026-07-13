"""
FILE: cmfs/cmfs_backend/gate/serializers.py
ACTION: CREATE (Phase 8)
"""

from decimal import Decimal
from rest_framework import serializers

from delegates.models import Delegate


class GateDelegateSerializer(serializers.ModelSerializer):
    """
    Everything a Gate Official's browser needs cached in memory for a
    convention, so a scan can be resolved entirely offline: identity,
    payment status/balance, and current attendance state. Loaded once at
    login via GET /api/gate/{unit_id}/delegates/, then kept in sync with
    the responses from the check-in endpoints as scans happen.
    """
    balance_owed = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    fee_amount = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    checked_in = serializers.SerializerMethodField()
    checked_in_at = serializers.SerializerMethodField()
    checked_in_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Delegate
        fields = [
            'id', 'delegate_id', 'full_name', 'category', 'county_id',
            'balance_owed', 'payment_status', 'fee_amount', 'total_paid',
            'checked_in', 'checked_in_at', 'checked_in_by_name',
        ]

    def _attendance(self, obj):
        # obj.attendance is a reverse OneToOne — accessing it raises
        # Delegate.attendance.RelatedObjectDoesNotExist (not AttributeError)
        # when no row exists yet, so getattr(..., default) alone won't
        # catch it; select_related('attendance') in the view avoids the
        # exception path entirely (sets this to None instead), but we
        # still guard here in case a caller forgot to select_related.
        try:
            return obj.attendance
        except Delegate.attendance.RelatedObjectDoesNotExist:
            return None

    def get_balance_owed(self, obj):
        return obj.balance_owed

    def get_payment_status(self, obj):
        return obj.payment_status

    def get_fee_amount(self, obj):
        return obj.fee_amount

    def get_total_paid(self, obj):
        return obj.total_paid

    def get_checked_in(self, obj):
        att = self._attendance(obj)
        return bool(att and att.checked_in)

    def get_checked_in_at(self, obj):
        att = self._attendance(obj)
        return att.checked_in_at if att and att.checked_in else None

    def get_checked_in_by_name(self, obj):
        att = self._attendance(obj)
        return att.checked_in_by_name if att and att.checked_in else ''


class SingleCheckinSerializer(serializers.Serializer):
    """POST /api/gate/checkin/ — mark one delegate attended (online path)."""
    delegate_id = serializers.CharField()
    timestamp = serializers.DateTimeField(required=False)


class BatchCheckinRecordSerializer(serializers.Serializer):
    """One record inside the array POSTed to /api/gate/checkin/batch/."""
    delegate_id = serializers.CharField()
    timestamp = serializers.DateTimeField()


class GateCashPaymentSerializer(serializers.Serializer):
    """POST /api/gate/checkin/cash-payment/ — online only."""
    delegate_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    notes = serializers.CharField(required=False, allow_blank=True, default='')
