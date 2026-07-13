"""
FILE: cmfs/cmfs_backend/budget/views.py
ACTION: MODIFY (Phase 9 additions)

Endpoints:
  GET/POST   /api/units/<unit_id>/budget/income/
  PATCH/DEL  /api/budget/income/<id>/
  GET/POST   /api/units/<unit_id>/budget/expenses/
  PATCH/DEL  /api/budget/expenses/<id>/
  GET        /api/units/<unit_id>/budget/summary/
  GET        /api/budget/expense-items/preloaded/

  GET/POST   /api/units/<unit_id>/actuals/expenses/     (Phase 9)
  POST       /api/units/<unit_id>/actuals/unbudgeted/    (Phase 9)
  GET        /api/units/<unit_id>/actuals/summary/       (Phase 9)
  GET        /api/units/<unit_id>/actuals/outstanding/    (Phase 9)

DO NOT BUILD YET (Phase 9 scope note, carried over from Phase 5): no
OpenPyXL/ReportLab report generation here — that's Phase 10. This file
stays limited to data entry and DB state changes.
"""

from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.response import Response

from auth_app.utils import get_client_ip
from auth_app.audit import log as audit_log
from auth_app.permissions import (
    IsAuthenticated,
    IsFinanceViewerOrAbove,
    IsBudgetCreatorOrAbove,
    user_can_access_unit,
)
from conventions.models import ConventionUnit

from .models import BudgetIncome, BudgetExpenseItem, PreloadedExpenseItem, ActualExpense
from .serializers import (
    PreloadedExpenseItemSerializer,
    BudgetIncomeSerializer,
    BudgetIncomeCreateSerializer,
    BudgetIncomeActualSerializer,
    BudgetExpenseItemSerializer,
    BudgetExpenseItemCreateSerializer,
    BudgetExpenseItemUpdateSerializer,
    ActualExpenseSerializer,
    ActualExpenseCreateSerializer,
    UnbudgetedExpenseCreateSerializer,
)

MISC_RATE = Decimal('0.05')


def _get_unit_or_404(unit_id):
    try:
        return ConventionUnit.objects.select_related('convention').get(pk=unit_id)
    except ConventionUnit.DoesNotExist:
        return None


def _next_item_code(convention_unit, category, is_unbudgeted=False):
    prefix = 'UNB' if is_unbudgeted else 'EXP'
    existing = BudgetExpenseItem.objects.filter(
        convention_unit=convention_unit, category=category, is_unbudgeted=is_unbudgeted,
    ).count()
    seq = existing + 1
    return f"{prefix}-{category}-{seq:03d}"


def _next_voucher_number(convention_unit):
    """PV01, PV02, ... — one shared sequence per unit, budgeted or unbudgeted alike."""
    existing = ActualExpense.objects.filter(budget_expense_item__convention_unit=convention_unit).count()
    return f"PV{existing + 1:02d}"


# ── Preloaded expense items ────────────────────────────────────────────────────

class PreloadedExpenseItemListView(APIView):
    """GET /api/budget/expense-items/preloaded/ — all 50+ items, not unit-specific."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = PreloadedExpenseItem.objects.all()
        serializer = PreloadedExpenseItemSerializer(items, many=True)
        return Response({'items': serializer.data})


# ── Budget income ───────────────────────────────────────────────────────────────

class BudgetIncomeView(APIView):
    """
    GET  /api/units/<unit_id>/budget/income/  — list this unit's income estimates
    POST /api/units/<unit_id>/budget/income/  — create/update an estimate for a category
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        if not IsFinanceViewerOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        unit = _get_unit_or_404(unit_id)
        if not unit:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        incomes = BudgetIncome.objects.filter(convention_unit=unit)
        serializer = BudgetIncomeSerializer(incomes, many=True)
        total = sum((i.estimated_total for i in incomes), Decimal('0'))
        return Response({'incomes': serializer.data, 'total_estimated_income': total})

    def post(self, request, unit_id):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        unit = _get_unit_or_404(unit_id)
        if not unit:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = BudgetIncomeCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        category = data['category']
        convention = unit.convention

        if category == 'student':
            unit_fee = convention.fee_student
            count = data['estimated_count']
            total = unit_fee * count
        elif category == 'kessat':
            unit_fee = convention.fee_kessat
            count = data['estimated_count']
            total = unit_fee * count
        elif category == 'associate':
            unit_fee = convention.fee_associate
            count = data['estimated_count']
            total = unit_fee * count
        else:
            # offering / exhibition — free-text estimated amount
            unit_fee = Decimal('0')
            count = 0
            total = data['estimated_total']

        income, _created = BudgetIncome.objects.update_or_create(
            convention_unit=unit, category=category,
            defaults={
                'estimated_count': count,
                'unit_fee': unit_fee,
                'estimated_total': total,
            },
        )

        audit_log(
            user=request.auth_user,
            action='budget_income_saved',
            detail=f'Budget income ({category}) saved for unit id={unit.id}: {total}',
            ip=get_client_ip(request),
        )

        return Response({'income': BudgetIncomeSerializer(income).data}, status=201)


class BudgetIncomeDetailView(APIView):
    """PATCH/DELETE /api/budget/income/<id>/"""
    permission_classes = [IsAuthenticated]

    def _get_income_or_404(self, pk):
        try:
            return BudgetIncome.objects.select_related('convention_unit').get(pk=pk)
        except BudgetIncome.DoesNotExist:
            return None

    def patch(self, request, pk):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        income = self._get_income_or_404(pk)
        if not income:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, income.convention_unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = BudgetIncomeCreateSerializer(data={**request.data, 'category': income.category})
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        convention = income.convention_unit.convention
        category = income.category

        if category in ('student', 'kessat', 'associate'):
            fee = {'student': convention.fee_student, 'kessat': convention.fee_kessat,
                   'associate': convention.fee_associate}[category]
            income.estimated_count = data['estimated_count']
            income.unit_fee = fee
            income.estimated_total = fee * data['estimated_count']
        else:
            income.estimated_total = data['estimated_total']
        income.save()

        return Response({'income': BudgetIncomeSerializer(income).data})

    def delete(self, request, pk):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        income = self._get_income_or_404(pk)
        if not income:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, income.convention_unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        income.delete()
        return Response({'message': 'Income estimate deleted.'})


class BudgetIncomeActualView(APIView):
    """
    PATCH /api/budget/income/<id>/actual/

    Records the actual amount collected for an offering/exhibition income
    line — the only income categories without a Payment-derived actual,
    since they aren't tied to any Delegate. student/kessat/associate actuals
    are always computed live from confirmed payments and are rejected here.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            income = BudgetIncome.objects.select_related('convention_unit').get(pk=pk)
        except BudgetIncome.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if not user_can_access_unit(request.auth_user, income.convention_unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        if income.category not in ('offering', 'exhibition'):
            return Response({
                'error': 'Actuals for student/kessat/associate are computed automatically '
                         'from confirmed payments and cannot be entered manually.',
                'code': 'not_manual',
            }, status=400)

        serializer = BudgetIncomeActualSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        income.actual_total = serializer.validated_data['actual_total']
        income.save(update_fields=['actual_total'])
        return Response({'income': BudgetIncomeSerializer(income).data})


# ── Budget expense items ────────────────────────────────────────────────────────

class BudgetExpenseItemsView(APIView):
    """
    GET  /api/units/<unit_id>/budget/expenses/  — list this unit's budgeted items
    POST /api/units/<unit_id>/budget/expenses/  — add a preloaded or custom item
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        if not IsFinanceViewerOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        unit = _get_unit_or_404(unit_id)
        if not unit:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        items = BudgetExpenseItem.objects.filter(convention_unit=unit, is_unbudgeted=False)
        serializer = BudgetExpenseItemSerializer(items, many=True)
        total = sum((i.estimated_total for i in items), Decimal('0'))
        return Response({'items': serializer.data, 'total_estimated_expenses': total})

    def post(self, request, unit_id):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        unit = _get_unit_or_404(unit_id)
        if not unit:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = BudgetExpenseItemCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        preloaded_id = data.get('preloaded_item_id')
        is_custom = not bool(preloaded_id)

        if preloaded_id:
            try:
                preloaded = PreloadedExpenseItem.objects.get(pk=preloaded_id)
            except PreloadedExpenseItem.DoesNotExist:
                return Response(
                    {'error': 'Preloaded item not found.', 'code': 'not_found'}, status=400
                )
            item_name = preloaded.name
            category = preloaded.category
            unit_label = data.get('unit') or preloaded.default_unit
        else:
            item_name = data['item_name']
            category = data['category']
            unit_label = data.get('unit', '')

        qty = data['quantity']
        price = data['unit_price']
        days = data.get('days', 1)
        total = qty * price * days

        item_code = _next_item_code(unit, category, is_unbudgeted=False)

        item = BudgetExpenseItem.objects.create(
            convention_unit=unit,
            item_code=item_code,
            item_name=item_name,
            category=category,
            unit=unit_label,
            estimated_qty=qty,
            unit_price=price,
            days=days,
            estimated_total=total,
            is_custom=is_custom,
            is_unbudgeted=False,
            created_by_id=request.auth_user.id,
        )

        audit_log(
            user=request.auth_user,
            action='budget_expense_item_created',
            detail=f'Budget expense item {item_code} ({item_name}) created for unit id={unit.id}',
            ip=get_client_ip(request),
        )

        return Response({'item': BudgetExpenseItemSerializer(item).data}, status=201)


class BudgetExpenseItemDetailView(APIView):
    """PATCH/DELETE /api/budget/expenses/<id>/"""
    permission_classes = [IsAuthenticated]

    def _get_item_or_404(self, pk):
        try:
            return BudgetExpenseItem.objects.select_related('convention_unit').get(pk=pk)
        except BudgetExpenseItem.DoesNotExist:
            return None

    def patch(self, request, pk):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        item = self._get_item_or_404(pk)
        if not item:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, item.convention_unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = BudgetExpenseItemUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)

        data = serializer.validated_data
        if 'item_name' in data:
            item.item_name = data['item_name']
        if 'unit' in data:
            item.unit = data['unit']
        if 'quantity' in data:
            item.estimated_qty = data['quantity']
        if 'unit_price' in data:
            item.unit_price = data['unit_price']
        if 'days' in data:
            item.days = data['days']
        item.estimated_total = item.estimated_qty * item.unit_price * item.days
        item.save()

        return Response({'item': BudgetExpenseItemSerializer(item).data})

    def delete(self, request, pk):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        item = self._get_item_or_404(pk)
        if not item:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, item.convention_unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        item.delete()
        return Response({'message': 'Budget expense item deleted.'})


# ── Budget summary ───────────────────────────────────────────────────────────────

class BudgetSummaryView(APIView):
    """GET /api/units/<unit_id>/budget/summary/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        if not IsFinanceViewerOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        unit = _get_unit_or_404(unit_id)
        if not unit:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        incomes = BudgetIncome.objects.filter(convention_unit=unit)
        total_income = sum((i.estimated_total for i in incomes), Decimal('0'))

        expense_items = BudgetExpenseItem.objects.filter(convention_unit=unit, is_unbudgeted=False)
        total_direct_expenses = sum((i.estimated_total for i in expense_items), Decimal('0'))
        misc_total = (total_direct_expenses * MISC_RATE).quantize(Decimal('0.01'))
        total_expenses = total_direct_expenses + misc_total

        surplus_deficit = total_income - total_expenses

        return Response({
            'unit_id': unit.id,
            'total_estimated_income': total_income,
            'total_direct_expenses': total_direct_expenses,
            'misc_expenses_5pct': misc_total,
            'total_estimated_expenses': total_expenses,
            'surplus_deficit': surplus_deficit,
            'income_by_category': {
                i.category: str(i.estimated_total) for i in incomes
            },
        })


# ── Actual expenses (Phase 9) ────────────────────────────────────────────────────

class ActualExpensesView(APIView):
    """
    GET  /api/units/<unit_id>/actuals/expenses/  — every actual expense (budgeted + unbudgeted) for a unit
    POST /api/units/<unit_id>/actuals/expenses/  — record actual spend against an existing budgeted item
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        if not IsFinanceViewerOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        unit = _get_unit_or_404(unit_id)
        if not unit:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        actuals = (
            ActualExpense.objects
            .filter(budget_expense_item__convention_unit=unit)
            .select_related('budget_expense_item')
        )
        return Response({'actual_expenses': ActualExpenseSerializer(actuals, many=True).data})

    def post(self, request, unit_id):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        unit = _get_unit_or_404(unit_id)
        if not unit:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = ActualExpenseCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)
        data = serializer.validated_data

        try:
            item = BudgetExpenseItem.objects.get(pk=data['budget_expense_item_id'], convention_unit=unit)
        except BudgetExpenseItem.DoesNotExist:
            return Response({'error': 'Budget expense item not found for this unit.', 'code': 'not_found'}, status=404)

        qty = data['actual_qty']
        price = data['actual_unit_price']
        total = qty * price
        voucher = _next_voucher_number(unit)

        # entered_by is ALWAYS from the JWT (request.auth_user) — never
        # taken from the request body, even if the client sends one.
        actual = ActualExpense.objects.create(
            budget_expense_item=item,
            actual_qty=qty,
            actual_unit_price=price,
            actual_total=total,
            authorized_by=data['authorized_by'],
            received_by=data['received_by'],
            entered_by_id=request.auth_user.id,
            entered_by_name=request.auth_user.full_name,
            voucher_number=voucher,
            notes=data.get('notes', ''),
        )

        audit_log(
            user=request.auth_user, action='actual_expense_recorded',
            detail=f'Actual expense {voucher} ({item.item_code}) recorded for unit id={unit.id}: KES {total}',
            ip=get_client_ip(request),
        )

        return Response({'actual_expense': ActualExpenseSerializer(actual).data}, status=201)


class ActualExpenseDetailView(APIView):
    """
    DELETE /api/budget/actuals/<id>/
    Budget Creator or above. Lets a mis-keyed actual-expense entry (wrong
    qty, wrong price, wrong item selected, duplicate entry, etc.) be
    removed. If the entry was against an unbudgeted item, its
    auto-created BudgetExpenseItem (UNB-...) is removed together with
    it — that item exists solely to hold this one actual expense, so
    leaving it behind would strand an empty, orphaned budget line.
    Entries against a normal budgeted item leave that budget line intact;
    only the actual-spend record itself is removed.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        try:
            actual = ActualExpense.objects.select_related('budget_expense_item__convention_unit').get(pk=pk)
        except ActualExpense.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        item = actual.budget_expense_item
        if not user_can_access_unit(request.auth_user, item.convention_unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        voucher = actual.voucher_number
        was_unbudgeted = item.is_unbudgeted

        actual.delete()
        if was_unbudgeted:
            item.delete()

        audit_log(
            user=request.auth_user, action='actual_expense_deleted',
            detail=f'Deleted actual expense {voucher} ({item.item_code}) for unit id={item.convention_unit_id}'
                   + (' — unbudgeted item removed with it' if was_unbudgeted else ''),
            ip=get_client_ip(request),
        )

        return Response({'message': f'Actual expense {voucher} deleted.'})


class UnbudgetedExpenseView(APIView):
    """
    POST /api/units/<unit_id>/actuals/unbudgeted/
    Creates a fresh BudgetExpenseItem (is_unbudgeted=True, item_code
    UNB-{CATEGORY}-{SEQ}) first — there's no pre-existing budget line to
    attach an unbudgeted spend to — then records the ActualExpense
    against it, sharing the same PV voucher sequence as budgeted items.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, unit_id):
        if not IsBudgetCreatorOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        unit = _get_unit_or_404(unit_id)
        if not unit:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        serializer = UnbudgetedExpenseCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'validation_error'}, status=400)
        data = serializer.validated_data

        item_code = _next_item_code(unit, data['category'], is_unbudgeted=True)
        qty = data['actual_qty']
        price = data['actual_unit_price']
        total = qty * price

        item = BudgetExpenseItem.objects.create(
            convention_unit=unit,
            item_code=item_code,
            item_name=data['item_name'],
            category=data['category'],
            unit=data.get('unit', ''),
            estimated_qty=0,
            unit_price=0,
            days=1,
            estimated_total=0,
            is_custom=True,
            is_unbudgeted=True,
            created_by_id=request.auth_user.id,
        )

        voucher = _next_voucher_number(unit)
        actual = ActualExpense.objects.create(
            budget_expense_item=item,
            actual_qty=qty,
            actual_unit_price=price,
            actual_total=total,
            authorized_by=data['authorized_by'],
            received_by=data['received_by'],
            entered_by_id=request.auth_user.id,
            entered_by_name=request.auth_user.full_name,
            voucher_number=voucher,
            notes=data.get('notes', ''),
        )

        audit_log(
            user=request.auth_user, action='unbudgeted_expense_recorded',
            detail=f'Unbudgeted expense {item_code} / voucher {voucher} recorded for unit id={unit.id}: KES {total}',
            ip=get_client_ip(request),
        )

        return Response({
            'item': BudgetExpenseItemSerializer(item).data,
            'actual_expense': ActualExpenseSerializer(actual).data,
        }, status=201)


class OutstandingPaymentsView(APIView):
    """GET /api/units/<unit_id>/actuals/outstanding/ — all INCOMPLETE/NOT_PAID delegates for a unit."""
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        if not IsFinanceViewerOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        unit = _get_unit_or_404(unit_id)
        if not unit:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        from delegates.models import Delegate
        from delegates.serializers import DelegateSerializer

        qs = Delegate.objects.filter(convention=unit.convention, registration_status='active')
        if unit.scope_type == 'county':
            qs = qs.filter(county=unit.county)
        elif unit.scope_type == 'regional':
            qs = qs.filter(county__region=unit.region)

        outstanding = [d for d in qs if d.payment_status in ('INCOMPLETE', 'NOT_PAID')]
        return Response({'delegates': DelegateSerializer(outstanding, many=True).data, 'total': len(outstanding)})


class ActualsSummaryView(APIView):
    """
    GET /api/units/<unit_id>/actuals/summary/
    total_actual_income is cash actually collected (unaffected by a
    write-off — forgiving a balance never manufactures income that
    wasn't paid). A write-off's effect shows up in
    total_outstanding_after_writeoffs, which is what "amount deducted
    from income totals" means here: it reduces what the county is still
    expected to bring in, not what it already has.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        if not IsFinanceViewerOrAbove().has_permission(request, self):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        unit = _get_unit_or_404(unit_id)
        if not unit:
            return Response({'error': 'Convention unit not found.', 'code': 'not_found'}, status=404)
        if not user_can_access_unit(request.auth_user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        from delegates.models import Delegate, WriteOff
        from budget.models import BudgetIncome

        delegate_qs = Delegate.objects.filter(convention=unit.convention, registration_status='active')
        if unit.scope_type == 'county':
            delegate_qs = delegate_qs.filter(county=unit.county)
        elif unit.scope_type == 'regional':
            delegate_qs = delegate_qs.filter(county__region=unit.region)

        delegate_actual_income = sum((d.total_paid for d in delegate_qs), Decimal('0'))

        # offering/exhibition aren't tied to any Delegate/Payment — they're
        # manually recorded on BudgetIncome.actual_total (see
        # BudgetIncomeActualView) and must be folded in here too, or this
        # summary silently omits them the way it did before this fix.
        other_income_qs = BudgetIncome.objects.filter(
            convention_unit=unit, category__in=('offering', 'exhibition')
        )
        other_actual_income = sum(
            (bi.actual_total for bi in other_income_qs if bi.actual_total is not None), Decimal('0')
        )

        total_actual_income = delegate_actual_income + other_actual_income
        total_outstanding_before_writeoffs = sum((d.balance_owed for d in delegate_qs), Decimal('0'))

        write_offs = WriteOff.objects.filter(delegate__in=list(delegate_qs))
        total_written_off = sum((w.amount_written_off for w in write_offs), Decimal('0'))
        total_outstanding_after_writeoffs = total_outstanding_before_writeoffs - total_written_off

        actuals = ActualExpense.objects.filter(budget_expense_item__convention_unit=unit)
        total_actual_expenses = sum((a.actual_total for a in actuals), Decimal('0'))

        surplus_deficit = total_actual_income - total_actual_expenses

        return Response({
            'unit_id': unit.id,
            'total_actual_income': total_actual_income,
            'total_actual_expenses': total_actual_expenses,
            'surplus_deficit': surplus_deficit,
            'total_outstanding_before_writeoffs': total_outstanding_before_writeoffs,
            'total_written_off': total_written_off,
            'total_outstanding_after_writeoffs': total_outstanding_after_writeoffs,
        })