from rest_framework.permissions import BasePermission


class IsAuthenticated(BasePermission):
    """Requires a valid JWT (set by JWTAuthMiddleware)."""
    def has_permission(self, request, view):
        return request.auth_user is not None


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.auth_user is not None and request.auth_user.role == 'super_admin'


class IsCountyHeadOrAbove(BasePermission):
    ALLOWED = {'super_admin', 'national_head', 'regional_head', 'county_head'}

    def has_permission(self, request, view):
        return (
            request.auth_user is not None
            and request.auth_user.role in self.ALLOWED
        )