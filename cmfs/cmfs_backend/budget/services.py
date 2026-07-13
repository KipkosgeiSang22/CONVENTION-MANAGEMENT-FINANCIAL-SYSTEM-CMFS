"""
FILE: cmfs/cmfs_backend/budget/services.py
ACTION: CREATE (Phase 10 patch)

Small, focused query helpers that sit above the raw models. Kept separate
from models.py so it's obvious these are read/aggregation helpers, not
schema.
"""

from decimal import Decimal

# The three "named people" expense categories that the reference financial
# statement tracks via separate name-lists (kitchen/security/catering staff,
# guest speakers, and organizing-committee/volunteer appreciation).
PEOPLE_APPRECIATION_CATEGORIES = ['STAFF', 'SPEAK', 'APPR']


def get_people_appreciation_actuals(convention_unit):
    """
    Returns actual-spend totals for the three 'named people' expense
    categories — Catering Staff, Speaker Tokens, and Workers & Appreciation
    — for a given ConventionUnit, pulled live from ActualExpense records
    (not cached/estimated figures).

    This exists because these three categories previously had no single
    place pulling their combined actual spend for reporting — Catering
    Staff and Speaker Tokens already existed as categories, but there was
    no 'Workers & Appreciation' category at all until this patch, so the
    organizing-committee/volunteer appreciation payouts had nowhere to be
    recorded or reported on.

    Returns: {
        'STAFF': Decimal, 'SPEAK': Decimal, 'APPR': Decimal,
        'combined_total': Decimal,
    }
    """
    from budget.models import BudgetExpenseItem, ActualExpense

    totals = {}
    for cat in PEOPLE_APPRECIATION_CATEGORIES:
        items = BudgetExpenseItem.objects.filter(
            convention_unit=convention_unit, category=cat,
        )
        actuals = ActualExpense.objects.filter(budget_expense_item__in=items)
        totals[cat] = sum((a.actual_total for a in actuals), Decimal('0'))

    totals['combined_total'] = sum(
        (totals[cat] for cat in PEOPLE_APPRECIATION_CATEGORIES), Decimal('0')
    )
    return totals
