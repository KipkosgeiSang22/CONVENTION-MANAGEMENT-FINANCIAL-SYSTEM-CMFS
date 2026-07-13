"""
FILE: cmfs/cmfs_backend/budget/serializers.py
ACTION: CREATE (Phase 5)
"""

from decimal import Decimal

from rest_framework import serializers
from .models import BudgetIncome, BudgetExpenseItem, PreloadedExpenseItem, ActualExpense


class PreloadedExpenseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreloadedExpenseItem
        fields = ['id', 'name', 'category', 'default_unit']


class BudgetIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetIncome
        fields = [
            'id', 'convention_unit_id', 'category',
            'estimated_count', 'unit_fee', 'estimated_total', 'actual_total',
        ]
        read_only_fields = ['id', 'convention_unit_id', 'estimated_total']


class BudgetIncomeActualSerializer(serializers.Serializer):
    """
    offering/exhibition only — student/kessat/associate actuals are always
    derived live from confirmed Payment records and can't be overridden here.
    """
    actual_total = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class BudgetIncomeCreateSerializer(serializers.Serializer):
    """
    student/kessat/associate: estimated_count required, unit_fee resolved
    from the convention's fee schedule server-side (never trusted from client).
    offering/exhibition: estimated_total entered directly (free-text amount).
    """
    category = serializers.ChoiceField(choices=[c[0] for c in BudgetIncome.CATEGORY_CHOICES])
    estimated_count = serializers.IntegerField(required=False, min_value=0, default=0)
    estimated_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=0
    )

    def validate(self, data):
        category = data['category']
        if category in ('student', 'kessat', 'associate'):
            if not data.get('estimated_count'):
                raise serializers.ValidationError(
                    {'estimated_count': 'estimated_count is required for this category.'}
                )
        else:
            if data.get('estimated_total') is None:
                raise serializers.ValidationError(
                    {'estimated_total': 'estimated_total is required for this category.'}
                )
        return data


class BudgetExpenseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetExpenseItem
        fields = [
            'id', 'convention_unit_id', 'item_code', 'item_name', 'category',
            'unit', 'estimated_qty', 'unit_price', 'days', 'estimated_total',
            'is_custom', 'is_unbudgeted', 'created_by_id', 'created_at',
        ]
        read_only_fields = [
            'id', 'convention_unit_id', 'item_code', 'estimated_total',
            'is_unbudgeted', 'created_by_id', 'created_at',
        ]


class BudgetExpenseItemCreateSerializer(serializers.Serializer):
    """
    Either supply preloaded_item_id (dropdown selection) OR item_name +
    category (custom item). quantity/unit_price required; days optional
    (defaults to 1, matches the Budget Entry validation rule).
    """
    preloaded_item_id = serializers.IntegerField(required=False, allow_null=True)
    item_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    category = serializers.ChoiceField(
        choices=[c[0] for c in BudgetExpenseItem.CATEGORY_CHOICES], required=False
    )
    unit = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    days = serializers.IntegerField(required=False, min_value=1, default=1)

    def validate(self, data):
        if not data.get('preloaded_item_id') and not data.get('item_name'):
            raise serializers.ValidationError(
                'Either preloaded_item_id or item_name must be supplied.'
            )
        if not data.get('preloaded_item_id') and not data.get('category'):
            raise serializers.ValidationError(
                {'category': 'category is required for a custom item.'}
            )
        return data


class BudgetExpenseItemUpdateSerializer(serializers.Serializer):
    """Editable fields on an existing budget expense item."""
    item_name = serializers.CharField(max_length=200, required=False)
    unit = serializers.CharField(max_length=50, required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'), required=False)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'), required=False)
    days = serializers.IntegerField(min_value=1, required=False)


# ── Actual expenses (Phase 9) ────────────────────────────────────────────────────

class ActualExpenseSerializer(serializers.ModelSerializer):
    """Read serializer — includes the parent item's identity + budget/variance context."""
    item_code = serializers.CharField(source='budget_expense_item.item_code', read_only=True)
    item_name = serializers.CharField(source='budget_expense_item.item_name', read_only=True)
    category = serializers.CharField(source='budget_expense_item.category', read_only=True)
    is_unbudgeted = serializers.BooleanField(source='budget_expense_item.is_unbudgeted', read_only=True)
    estimated_total = serializers.DecimalField(
        source='budget_expense_item.estimated_total', max_digits=12, decimal_places=2, read_only=True,
    )
    variance = serializers.SerializerMethodField()

    class Meta:
        model = ActualExpense
        fields = [
            'id', 'budget_expense_item_id', 'item_code', 'item_name', 'category', 'is_unbudgeted',
            'estimated_total', 'actual_qty', 'actual_unit_price', 'actual_total', 'variance',
            'authorized_by', 'received_by', 'entered_by_id', 'entered_by_name',
            'voucher_number', 'timestamp', 'notes',
        ]
        read_only_fields = fields

    def get_variance(self, obj):
        return obj.actual_total - obj.budget_expense_item.estimated_total


class ActualExpenseCreateSerializer(serializers.Serializer):
    """POST /api/units/<unit_id>/actuals/expenses/ — against an existing budgeted item."""
    budget_expense_item_id = serializers.IntegerField()
    actual_qty = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    actual_unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    authorized_by = serializers.CharField(max_length=100)
    received_by = serializers.CharField(max_length=100)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class UnbudgetedExpenseCreateSerializer(serializers.Serializer):
    """POST /api/units/<unit_id>/actuals/unbudgeted/ — creates its own BudgetExpenseItem first."""
    item_name = serializers.CharField(max_length=200)
    category = serializers.ChoiceField(choices=[c[0] for c in BudgetExpenseItem.CATEGORY_CHOICES])
    unit = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    actual_qty = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    actual_unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    authorized_by = serializers.CharField(max_length=100)
    received_by = serializers.CharField(max_length=100)
    notes = serializers.CharField(required=False, allow_blank=True, default='')