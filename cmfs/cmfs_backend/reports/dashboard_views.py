"""
FILE: cmfs/cmfs_backend/reports/dashboard_views.py
ACTION: CREATE (Phase 11)

One adaptive endpoint, GET /api/dashboard/, that returns the right shape
of data for whoever's asking:
  - county_head / county-scoped budget_creator|finance_viewer|gate_official
      -> delegate counts, payment totals, income vs budget breakdown,
         outstanding items list, for their own county's live convention unit.
  - regional_head / region-scoped operational roles
      -> the above, plus a county-level breakdown across their region and
         regional totals.
  - national_head
      -> a region-level breakdown across the whole convention and national
         totals.
  - super_admin
      -> all conventions, all units, and basic system health counters.

Reuses reports.generators.aggregate_data so these numbers are always
computed the same way as the downloadable reports (Phase 10) — never a
second, drifting implementation of "how do we count a delegate".
"""

from rest_framework.views import APIView
from rest_framework.response import Response

from auth_app.permissions import IsAuthenticated, IsSuperAdmin, user_can_access_unit
from conventions.models import Convention, ConventionUnit

from .generators import aggregate_data
from .models import Report, AnnualSummary


# ── Shared helpers ────────────────────────────────────────────────────────────

_LIVE_STATUSES_PRIORITY = {
    Convention.STATUS_ACTIVE: 0,
    Convention.STATUS_ENDED: 1,
    Convention.STATUS_OPEN: 2,
    Convention.STATUS_FINANCIALLY_CLOSED: 3,
    Convention.STATUS_ARCHIVED: 4,
}


def _resolve_relevant_unit(user):
    """
    Picks the single most relevant ConventionUnit for this user right now:
    the accessible unit whose convention is furthest along but not yet
    archived (ACTIVE > ENDED > OPEN > FINANCIALLY_CLOSED > ARCHIVED),
    breaking ties by most recently created. Returns (unit, convention) or
    (None, None) if nothing currently covers this user's geography.
    """
    candidates = (
        ConventionUnit.objects
        .select_related('convention', 'county', 'region')
        .exclude(convention__status=Convention.STATUS_DRAFT)
    )
    best = None
    for unit in candidates:
        if not user_can_access_unit(user, unit):
            continue
        priority = _LIVE_STATUSES_PRIORITY.get(unit.convention.status, 99)
        key = (priority, -unit.convention.created_at.timestamp())
        if best is None or key < best[0]:
            best = (key, unit)
    return (best[1], best[1].convention) if best else (None, None)


def _income_vs_budget_chart(data: dict) -> list:
    """A flat list of {label, budgeted, actual} bars: one per income category
    (excluding Offering/Exhibition, which have no fixed per-delegate budget
    target) plus one per expenditure category group — enough for a simple
    income-vs-budget bar chart without introducing a charting library."""
    bars = []
    for il in data['income_lines']:
        if il['category'] in ('Offering', 'Exhibition'):
            continue
        bars.append({'label': f"Income: {il['category']}", 'budgeted': float(il['estimated']), 'actual': float(il['actual'])})
    for group in data['category_groups']:
        bars.append({
            'label': f"Expense: {group['category_label']}",
            'budgeted': float(group['budgeted_subtotal']),
            'actual': float(group['actual_subtotal']),
        })
    return bars


def _unit_summary(unit, data: dict) -> dict:
    return {
        'unit_id': unit.id,
        'scope_type': unit.scope_type,
        'display_name': unit.display_name,
        'delegate_count': data['delegate_count'],
        'checked_in_count': data['checked_in_count'],
        'total_income': data['total_income'],
        'total_expenditure': data['total_expenditure'],
        'net_balance': data['net_balance'],
    }


# ── Main adaptive dashboard endpoint ──────────────────────────────────────────

class DashboardView(APIView):
    """GET /api/dashboard/ — shape depends on request.auth_user.role/scope."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.auth_user

        if user.role == 'super_admin':
            return Response(_super_admin_dashboard())

        unit, convention = _resolve_relevant_unit(user)
        if unit is None:
            return Response({
                'role': user.role,
                'has_live_convention': False,
                'message': 'No live convention currently covers your assigned geography.',
            })

        if user.role == 'national_head':
            return Response(_national_dashboard(user, convention))
        if user.role == 'regional_head':
            return Response(_regional_dashboard(user, convention, unit))

        # county_head and county/region/national-scoped operational roles
        # (budget_creator, finance_viewer, gate_official) all get the same
        # "county-style" single-unit view, scoped to whichever unit
        # _resolve_relevant_unit found for them.
        return Response(_county_style_dashboard(user, convention, unit))


def _county_style_dashboard(user, convention, unit):
    try:
        data = aggregate_data(convention, unit)
    except Exception as e:
        return {
            'role': user.role, 'has_live_convention': True,
            'convention_id': convention.id, 'convention_name': convention.name,
            'error': f'Could not compute dashboard data: {e}',
        }
    return {
        'role': user.role,
        'has_live_convention': True,
        'convention_id': convention.id,
        'convention_name': convention.name,
        'convention_status': convention.status,
        'unit': _unit_summary(unit, data),
        'income_vs_budget': _income_vs_budget_chart(data),
        'outstanding_items': data['outstanding_rows'],
        'write_offs': data['write_off_rows'],
    }


def _regional_dashboard(user, convention, unit):
    """County-level breakdown across the region, plus regional totals."""
    county_units = [
        u for u in convention.units.select_related('county', 'region').all()
        if u.scope_type == 'county' and u.county_id and u.county.region_id == user.region_id
    ]

    breakdown = []
    total_income = total_expenditure = 0
    total_delegates = total_checked_in = 0
    for cu in county_units:
        try:
            cdata = aggregate_data(convention, cu)
        except Exception:
            continue
        breakdown.append(_unit_summary(cu, cdata))
        total_income += cdata['total_income']
        total_expenditure += cdata['total_expenditure']
        total_delegates += cdata['delegate_count']
        total_checked_in += cdata['checked_in_count']

    # The regional_head's own unit (a regional-scope ConventionUnit, when
    # the convention itself has one — e.g. a national convention with one
    # unit per region) gives the authoritative regional total/income-vs-
    # budget view; falls back to the summed county data above when this
    # convention has no dedicated regional-scope unit for them.
    own_data = None
    if unit.scope_type == 'regional':
        try:
            own_data = aggregate_data(convention, unit)
        except Exception:
            own_data = None

    return {
        'role': user.role,
        'has_live_convention': True,
        'convention_id': convention.id,
        'convention_name': convention.name,
        'convention_status': convention.status,
        'regional_totals': {
            'total_income': own_data['total_income'] if own_data else total_income,
            'total_expenditure': own_data['total_expenditure'] if own_data else total_expenditure,
            'net_balance': (own_data['net_balance'] if own_data else total_income - total_expenditure),
            'delegate_count': own_data['delegate_count'] if own_data else total_delegates,
            'checked_in_count': own_data['checked_in_count'] if own_data else total_checked_in,
        },
        'income_vs_budget': _income_vs_budget_chart(own_data) if own_data else [],
        'county_breakdown': sorted(breakdown, key=lambda r: r['display_name']),
        'outstanding_items': own_data['outstanding_rows'] if own_data else [],
    }


def _national_dashboard(user, convention):
    """Region-level breakdown across the whole convention, plus national totals."""
    from conventions.models import Region

    try:
        overall = aggregate_data(convention, unit=None)
    except Exception as e:
        return {
            'role': user.role, 'has_live_convention': True,
            'convention_id': convention.id, 'convention_name': convention.name,
            'error': f'Could not compute dashboard data: {e}',
        }

    county_units = [u for u in convention.units.select_related('county__region').all() if u.scope_type == 'county' and u.county_id]
    regional_units = [u for u in convention.units.select_related('region').all() if u.scope_type == 'regional' and u.region_id]

    region_breakdown = {}

    def _bucket(region):
        return region_breakdown.setdefault(region.id, {
            'region_id': region.id, 'region_name': region.name,
            'delegate_count': 0, 'checked_in_count': 0,
            'total_income': 0, 'total_expenditure': 0, 'net_balance': 0,
        })

    for ru in regional_units:
        try:
            rdata = aggregate_data(convention, ru)
        except Exception:
            continue
        b = _bucket(ru.region)
        b['delegate_count'] += rdata['delegate_count']
        b['checked_in_count'] += rdata['checked_in_count']
        b['total_income'] += rdata['total_income']
        b['total_expenditure'] += rdata['total_expenditure']
        b['net_balance'] += rdata['net_balance']

    if not regional_units:
        # Convention has per-county units only (no dedicated regional
        # units) — derive the region breakdown by summing each county's
        # own aggregate into its parent region's bucket instead.
        for cu in county_units:
            if not cu.county.region_id:
                continue
            try:
                cdata = aggregate_data(convention, cu)
            except Exception:
                continue
            b = _bucket(cu.county.region)
            b['delegate_count'] += cdata['delegate_count']
            b['checked_in_count'] += cdata['checked_in_count']
            b['total_income'] += cdata['total_income']
            b['total_expenditure'] += cdata['total_expenditure']
            b['net_balance'] += cdata['net_balance']

    return {
        'role': user.role,
        'has_live_convention': True,
        'convention_id': convention.id,
        'convention_name': convention.name,
        'convention_status': convention.status,
        'national_totals': {
            'total_income': overall['total_income'],
            'total_expenditure': overall['total_expenditure'],
            'net_balance': overall['net_balance'],
            'delegate_count': overall['delegate_count'],
            'checked_in_count': overall['checked_in_count'],
        },
        'income_vs_budget': _income_vs_budget_chart(overall),
        'region_breakdown': sorted(region_breakdown.values(), key=lambda r: r['region_name']),
        'outstanding_items': overall['outstanding_rows'],
    }


def _super_admin_dashboard():
    """All conventions, all units, plus basic system-health counters."""
    from auth_app.models import User

    conventions = Convention.objects.prefetch_related('units').order_by('-created_at')
    convention_list = [{
        'id': c.id, 'name': c.name, 'scope': c.scope, 'status': c.status,
        'unit_count': c.units.count(),
        'start_date': c.start_date, 'end_date': c.end_date,
    } for c in conventions]

    status_counts = {}
    for c in conventions:
        status_counts[c.status] = status_counts.get(c.status, 0) + 1

    role_counts = {}
    for row in User.objects.values('role').distinct():
        role = row['role']
        role_counts[role] = User.objects.filter(role=role).count()

    failed_reports = Report.objects.filter(status='failed').count()
    pending_reports = Report.objects.filter(status='pending').count()

    from datetime import timedelta
    from django.utils import timezone as dj_tz
    from .models import AuditLog
    recent_audit_activity = AuditLog.objects.filter(timestamp__gte=dj_tz.now() - timedelta(hours=24)).count()

    annual_summaries = list(
        AnnualSummary.objects.order_by('-year').values('year', 'status', 'generated_at')[:5]
    )

    return {
        'role': 'super_admin',
        'conventions': convention_list,
        'system_health': {
            'convention_status_counts': status_counts,
            'user_role_counts': role_counts,
            'failed_report_files': failed_reports,
            'pending_report_files': pending_reports,
            'audit_log_events_last_24h': recent_audit_activity,
        },
        'recent_annual_summaries': annual_summaries,
    }
