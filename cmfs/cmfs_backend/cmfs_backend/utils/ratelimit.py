"""
FILE: cmfs/cmfs_backend/cmfs_backend/utils/ratelimit.py
ACTION: CREATE (Phase 6)

This app has no django.contrib.auth session user — auth is via the custom
JWTAuthMiddleware, which sets request.auth_user. django-ratelimit's
built-in 'user' key assumes request.user, so endpoints that must be
limited per authenticated user (M-Pesa initiate, cash payments) use this
key function instead.
"""

from auth_app.utils import get_client_ip


def user_or_ip_key(group, request):
    user = getattr(request, 'auth_user', None)
    if user is not None:
        return f'user:{user.id}'
    return f'ip:{get_client_ip(request)}'