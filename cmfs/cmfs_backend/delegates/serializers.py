"""
FILE: cmfs/cmfs_backend/delegates/serializers.py
ACTION: CREATE (Phase 6)
"""

import re
from rest_framework import serializers

from auth_app.utils import normalize_kenyan_phone
from conventions.models import County
from .models import Delegate

NAME_RE = re.compile(r'^[A-Za-z\s\-]{3,100}$')


class PublicRegistrationSerializer(serializers.Serializer):
    """POST /api/delegates/register/ — no login required."""
    full_name = serializers.CharField(max_length=100)
    email = serializers.EmailField(required=True, allow_blank=False)
    category = serializers.ChoiceField(choices=[c[0] for c in Delegate.CATEGORY_CHOICES])
    county_id = serializers.IntegerField()
    parent_name = serializers.CharField(max_length=100)
    parent_phone = serializers.CharField(max_length=20)
    accept_terms = serializers.BooleanField()

    def validate_full_name(self, value):
        if not NAME_RE.match(value.strip()):
            raise serializers.ValidationError('Full name must be 3-100 letters, spaces, or hyphens only.')
        return value.strip()

    def validate_parent_name(self, value):
        if not re.match(r'^[A-Za-z\s]{3,100}$', value.strip()):
            raise serializers.ValidationError('Parent/Guardian name must be 3-100 letters and spaces only.')
        return value.strip()

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError('Email is required.')
        return value.lower().strip()

    def validate_parent_phone(self, value):
        normalized = normalize_kenyan_phone(value)
        if not normalized:
            raise serializers.ValidationError(
                'Enter a valid Kenyan mobile number (07XXXXXXXX, 01XXXXXXXX, or 2547XXXXXXXX).'
            )
        return normalized

    def validate_county_id(self, value):
        if not County.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Invalid county.')
        return value

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError('You must accept the Terms & Conditions.')
        return value


class ManualRegistrationSerializer(PublicRegistrationSerializer):
    """POST /api/delegates/manual/ — Budget Creator only. Adds payment fields."""
    payment_method = serializers.ChoiceField(choices=['cash', 'mpesa'])
    amount_received_now = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)


class DelegateSerializer(serializers.ModelSerializer):
    balance_owed = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    fee_amount = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    county_name = serializers.SerializerMethodField()

    class Meta:
        model = Delegate
        fields = [
            'id', 'delegate_id', 'full_name', 'category', 'parent_name', 'parent_phone',
            'email', 'county_id', 'county_name', 'convention_id', 'registration_status',
            'qr_code_path', 'registration_date', 'registered_by_id',
            'balance_owed', 'payment_status', 'fee_amount', 'total_paid',
        ]

    def get_balance_owed(self, obj):
        return obj.balance_owed

    def get_payment_status(self, obj):
        return obj.payment_status

    def get_fee_amount(self, obj):
        return obj.fee_amount

    def get_total_paid(self, obj):
        return obj.total_paid

    def get_county_name(self, obj):
        return obj.county.name