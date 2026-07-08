"""
FILE: cmfs/cmfs_backend/conventions/serializers.py
ACTION: CREATE (Phase 3)
"""

from rest_framework import serializers
from .models import Convention, ConventionUnit, County, Region


class CountySerializer(serializers.ModelSerializer):
    class Meta:
        model = County
        fields = ['id', 'name', 'county_code', 'region_id']


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name']


class ConventionUnitSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    county_name = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
# the above create virtual field int eh serializer. DRF looks for a method get_<field_name> to compute it's value
    class Meta:
        model = ConventionUnit
        fields = [
            'id', 'convention_id', 'scope_type', 'scope_id',
            'county_id', 'region_id',
            'display_name', 'county_name', 'region_name',
            'created_at',
        ]

    def get_display_name(self, obj):
        return obj.display_name

    def get_county_name(self, obj):
        return obj.county.name if obj.county else None

    def get_region_name(self, obj):
        return obj.region.name if obj.region else None


class ConventionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    unit_count = serializers.SerializerMethodField()

    class Meta:
        model = Convention
        fields = [
            'id', 'name', 'scope', 'status', 'start_date', 'end_date',
            'is_registration_open', 'scope_locked',
            'fee_student', 'fee_kessat', 'fee_associate',
            'created_at', 'unit_count',
        ]

    def get_unit_count(self, obj):
        return obj.units.count()#obj.units is the related manager for all ConventionUnit objects tied to that convention.


class ConventionDetailSerializer(serializers.ModelSerializer):
    """Full serializer including units for detail view."""
    units = ConventionUnitSerializer(many=True, read_only=True)

    class Meta:
        model = Convention
        fields = [
            'id', 'name', 'scope', 'status', 'description',
            'start_date', 'end_date',
            'is_registration_open', 'scope_locked',
            'fee_student', 'fee_kessat', 'fee_associate',
            # Lifecycle timestamps
            'published_at', 'started_at', 'ended_at',
            'financially_closed_at', 'archived_at',
            # Audit
            'created_by_id', 'financially_closed_by_id',
            'created_at', 'updated_at',
            # Related
            'units',
        ]


class ConventionCreateSerializer(serializers.Serializer):
    """
    Validates the 3-step wizard body.
    Step 1: name, start_date, end_date, description, fees
    Step 2: scope
    Step 3: units  (list of { scope_id })
    All three are submitted together in a single POST.
    """
    name = serializers.CharField(max_length=200)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    description = serializers.CharField(allow_blank=True, default='')
    scope = serializers.ChoiceField(choices=['county', 'regional', 'national'])
    fee_student = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    fee_kessat = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    fee_associate = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    # units: list of { scope_id: int|null }
    units = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )

    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError({'end_date': 'end_date must be after start_date.'})
        return data


class ConventionUpdateSerializer(serializers.Serializer):
    """
    Editable fields — only allowed while status == DRAFT.
    Scope cannot be changed after scope_locked=True.
    """
    name = serializers.CharField(max_length=200, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    fee_student = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)
    fee_kessat = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)
    fee_associate = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and start >= end:
            raise serializers.ValidationError({'end_date': 'end_date must be after start_date.'})
        return data


class ConventionTransitionSerializer(serializers.Serializer):
    """Used for lifecycle transitions that require TOTP confirmation."""
    totp_code = serializers.CharField(max_length=8, required=False, allow_blank=True)
    # For financial close — optional confirmation message
    confirm = serializers.BooleanField(default=False)
