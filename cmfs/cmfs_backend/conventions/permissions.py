"""
FILE: cmfs/cmfs_backend/conventions/permissions.py
ACTION: CREATE (Phase 3)
"""

from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, 'auth_user', None)
        return user is not None and user.role == 'super_admin'


class IsHeadOrAbove(BasePermission):
    """National Head, Regional Head, County Head, or Super Admin."""
    HEAD_ROLES = {'super_admin', 'national_head', 'regional_head', 'county_head'}

    def has_permission(self, request, view):
        user = getattr(request, 'auth_user', None)
        return user is not None and user.role in self.HEAD_ROLES


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, 'auth_user', None) is not None


def user_can_view_convention(user, convention):
    """
    Returns True if user is allowed to see this convention.
    Super Admin sees all. Head roles see conventions where they have a unit.

    budget_creator / finance_viewer / gate_official exist at every level
    (county, regional, national) and inherit their scope from whoever
    invited them — so their access has to be checked against whichever
    id they actually carry, not county_id alone.
    """
    if user.role == 'super_admin':
        return True
    if user.role == 'national_head':
        return True  # National head sees all conventions

    if user.role == 'regional_head':
        return convention.units.filter(region_id=user.region_id).exists()

    if user.role == 'county_head':
        return convention.units.filter(county_id=user.county_id).exists()

    if user.role in ('budget_creator', 'finance_viewer', 'gate_official'):
        if user.county_id:
            return convention.units.filter(county_id=user.county_id).exists()
        if user.region_id:
            return convention.units.filter(region_id=user.region_id).exists()
        # Neither set → this user was invited by a national_head,
        # so they're scoped to national conventions.
        return convention.scope == 'national'

    return False


def user_can_manage_convention(user, convention):
    """Can create/edit/transition convention."""
    if user.role == 'super_admin':
        return True
    if user.role == 'national_head' and convention.scope == 'national':
        return True
    #regional head code , I modified it, to confirm if it is correct
    if user.role == 'regional_head' and convention.scope == 'regional':
        return convention.units.filter(region_id=user.region_id).exists()

    if user.role == 'county_head' and convention.scope == 'county':
        # County head can manage their own convention unit
        return convention.units.filter(county_id=user.county_id).exists()
    return False
