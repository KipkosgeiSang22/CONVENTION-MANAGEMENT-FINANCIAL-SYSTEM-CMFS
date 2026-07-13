"""
FILE: cmfs/cmfs_backend/delegates/utils.py
ACTION: CREATE (Phase 6)
"""

from conventions.models import Convention, ConventionUnit, County


def list_open_conventions_for_county(county: County):
    """
    Returns every currently-registration-open (convention, unit) pair that
    covers this county — county-scope units first, then regional, then
    national. Unlike resolve_convention_for_county, this does NOT collapse
    to a single "most specific wins" answer: if a county convention and a
    regional convention (covering that county) are BOTH open at once, both
    are returned so the caller can be asked to disambiguate instead of one
    being silently picked for them.
    """
    matches = []

    county_units = (
        ConventionUnit.objects
        .filter(convention__is_registration_open=True, scope_type='county', county=county)
        .select_related('convention')
        .order_by('-convention__created_at')
    )
    matches += [(u.convention, u) for u in county_units]

    regional_units = (
        ConventionUnit.objects
        .filter(convention__is_registration_open=True, scope_type='regional', region=county.region)
        .select_related('convention')
        .order_by('-convention__created_at')
    )
    matches += [(u.convention, u) for u in regional_units]

    national_units = (
        ConventionUnit.objects
        .filter(convention__is_registration_open=True, scope_type='national')
        .select_related('convention')
        .order_by('-convention__created_at')
    )
    matches += [(u.convention, u) for u in national_units]

    return matches


def resolve_convention_for_county(county: County):
    """
    Finds the currently-registration-open Convention covering a given
    county, checking county-scope units first, then regional, then
    national (most specific match wins). Returns (convention, unit) or
    (None, None) if nothing is currently open for this county.

    Kept for any caller that just wants "the" answer (e.g. public
    self-registration, where there's no operator around to ask). Manual
    registration should prefer list_open_conventions_for_county directly
    so a genuine county/regional overlap isn't silently collapsed.
    """
    matches = list_open_conventions_for_county(county)
    return matches[0] if matches else (None, None)



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


def resolve_unit_for_delegate(delegate):
    """
    Phase 9 — WriteOff requires a convention_unit FK, but a Delegate only
    has a convention + county, not a direct unit link. Finds the most
    specific ConventionUnit covering this delegate: county-scoped first,
    then regional, then national — mirrors resolve_convention_for_county
    above, just run in the opposite direction (delegate -> unit instead
    of county -> convention).
    """
    unit = ConventionUnit.objects.filter(
        convention=delegate.convention, scope_type='county', county=delegate.county,
    ).first()
    if unit:
        return unit

    unit = ConventionUnit.objects.filter(
        convention=delegate.convention, scope_type='regional', region=delegate.county.region,
    ).first()
    if unit:
        return unit

    return ConventionUnit.objects.filter(convention=delegate.convention, scope_type='national').first()