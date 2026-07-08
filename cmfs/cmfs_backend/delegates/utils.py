"""
FILE: cmfs/cmfs_backend/delegates/utils.py
ACTION: CREATE (Phase 6)
"""

from conventions.models import Convention, ConventionUnit, County


def resolve_convention_for_county(county: County):
    """
    Finds the currently-registration-open Convention covering a given
    county, checking county-scope units first, then regional, then
    national (most specific match wins). Returns (convention, unit) or
    (None, None) if nothing is currently open for this county.
    """
    unit = (
        ConventionUnit.objects
        .filter(
            convention__is_registration_open=True,
            scope_type='county',
            county=county,
        )
        .select_related('convention')
        .order_by('-convention__created_at')
        .first()
    )
    if unit:
        return unit.convention, unit

    unit = (
        ConventionUnit.objects
        .filter(
            convention__is_registration_open=True,
            scope_type='regional',
            region=county.region,
        )
        .select_related('convention')
        .order_by('-convention__created_at')
        .first()
    )
    if unit:
        return unit.convention, unit

    unit = (
        ConventionUnit.objects
        .filter(
            convention__is_registration_open=True,
            scope_type='national',
        )
        .select_related('convention')
        .order_by('-convention__created_at')
        .first()
    )
    if unit:
        return unit.convention, unit

    return None, None


def generate_delegate_id(delegate) -> str:
    """
    {COUNTY_CODE}-{CATEGORY_CODE}-{YEAR}-{SEQUENCE}
    Sequence is per county + category + convention year, sequential,
    zero-padded to 4 digits. Called once, on first CONFIRMED payment.
    """
    from .models import Delegate

    year = delegate.convention.start_date.year
    county_code = delegate.county.county_code
    category_code = delegate.category_code

    existing = Delegate.objects.filter(
        county=delegate.county,
        category=delegate.category,
        convention__start_date__year=year,
    ).exclude(pk=delegate.pk).exclude(delegate_id__isnull=True).count()

    seq = existing + 1
    return f"{county_code}-{category_code}-{year}-{seq:04d}"