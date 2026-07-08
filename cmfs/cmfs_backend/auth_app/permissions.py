"""
FILE: cmfs/cmfs_backend/auth_app/permissions.py
ACTION: REPLACE (Phase 4 + scope fix)
"""

from rest_framework.permissions import BasePermission


# ── Base permission classes ────────────────────────────────────────────────────

class IsAuthenticated(BasePermission):
    """Requires a valid JWT (set by JWTAuthMiddleware)."""
    def has_permission(self, request, view):
        return request.auth_user is not None


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.auth_user is not None and request.auth_user.role == 'super_admin'


class IsNationalHead(BasePermission):
    def has_permission(self, request, view):
        return request.auth_user is not None and request.auth_user.role == 'national_head'


class IsRegionalHead(BasePermission):
    def has_permission(self, request, view):
        return request.auth_user is not None and request.auth_user.role == 'regional_head'


class IsCountyHead(BasePermission):
    def has_permission(self, request, view):
        return request.auth_user is not None and request.auth_user.role == 'county_head'


class IsBudgetCreator(BasePermission):
    def has_permission(self, request, view):
        return request.auth_user is not None and request.auth_user.role == 'budget_creator'


class IsFinanceViewer(BasePermission):
    def has_permission(self, request, view):
        return request.auth_user is not None and request.auth_user.role == 'finance_viewer'


class IsGateOfficial(BasePermission):
    def has_permission(self, request, view):
        return request.auth_user is not None and request.auth_user.role == 'gate_official'


# ── Compound permission classes ────────────────────────────────────────────────

class IsCountyHeadOrAbove(BasePermission):
    """County Head, Regional Head, National Head, or Super Admin."""
    ALLOWED = {'super_admin', 'national_head', 'regional_head', 'county_head'}

    def has_permission(self, request, view):
        return (
            request.auth_user is not None
            and request.auth_user.role in self.ALLOWED
        )


class IsHeadOrAbove(BasePermission):
    """Alias for IsCountyHeadOrAbove — kept for convention views compatibility."""
    ALLOWED = {'super_admin', 'national_head', 'regional_head', 'county_head'}

    def has_permission(self, request, view):
        return (
            request.auth_user is not None
            and request.auth_user.role in self.ALLOWED
        )


class IsBudgetCreatorOrAbove(BasePermission):
    """Budget Creator, County Head, or above."""
    ALLOWED = {'super_admin', 'national_head', 'regional_head', 'county_head', 'budget_creator'}

    def has_permission(self, request, view):
        return (
            request.auth_user is not None
            and request.auth_user.role in self.ALLOWED
        )


class IsFinanceViewerOrAbove(BasePermission):
    """Finance Viewer or any role above (read access to financial data)."""
    ALLOWED = {
        'super_admin', 'national_head', 'regional_head',
        'county_head', 'budget_creator', 'finance_viewer',
    }

    def has_permission(self, request, view):
        return (
            request.auth_user is not None
            and request.auth_user.role in self.ALLOWED
        )


# ── Invitation hierarchy ───────────────────────────────────────────────────────
#
# Maps each role to the set of roles it is allowed to invite via the API.
#
# Head roles (national_head, regional_head, county_head) are created by
# Super Admin via Django Admin or during convention creation — NOT via this
# invite API by other heads. Exception: Regional Head can invite county_head
# within their region (validated in InviteUserView).
#
# Operational roles are always invited by a head and inherit that head's
# county/region scope automatically. Convention-unit assignment happens
# later, via convention creation.

_INVITE_HIERARCHY = {
    'super_admin':    {'national_head', 'regional_head', 'county_head'},
    'national_head':  {'regional_head',
                       'budget_creator', 'finance_viewer', 'gate_official'},
    'regional_head':  {'county_head',
                       'budget_creator', 'finance_viewer', 'gate_official'},
    'county_head':    {'budget_creator', 'finance_viewer', 'gate_official'},
    'budget_creator': set(),
    'finance_viewer': set(),
    'gate_official':  set(),
    'delegate':       set(),
}


def can_invite_role(inviter_role: str, target_role: str) -> bool:
    """
    Returns True if a user with `inviter_role` is permitted to invite
    a user with `target_role`.
    """
    return target_role in _INVITE_HIERARCHY.get(inviter_role, set())


def get_invitable_roles(inviter_role: str) -> list:
    """Returns a sorted list of roles this role can invite."""
    return sorted(_INVITE_HIERARCHY.get(inviter_role, set()))


# ── Scope validation helpers ───────────────────────────────────────────────────

def user_can_access_county(user, county_id: int) -> bool:
    """
    Returns True if the user is allowed to access data for the given county.
    """
    if user.role == 'super_admin':
        return True
    if user.role == 'national_head':
        return True
    if user.role == 'regional_head':
        # Fine-grained check done in view with County query.
        return True
    # County-scoped roles must match exactly.
    return user.county_id == county_id


def user_can_access_region(user, region_id: int) -> bool:
    if user.role in ('super_admin', 'national_head'):
        return True
    if user.role == 'regional_head':
        return user.region_id == region_id
    return False


def user_can_access_unit(user, convention_unit) -> bool:
    """
    Returns True if the user has access to the given ConventionUnit.
    """
    if user.role == 'super_admin':
        return True
    if user.role == 'national_head':
        return True
    if user.role == 'regional_head':
        if convention_unit.scope_type == 'county':
            from conventions.models import County
            try:
                county = County.objects.get(pk=convention_unit.scope_id)
                return county.region_id == user.region_id
            except Exception:
                return False
        return convention_unit.scope_id == user.region_id
    # County-level roles must belong to the same county.
    if user.county_id is None:
        return False
    if convention_unit.scope_type == 'county':
        return convention_unit.scope_id == user.county_id
    return False