"""
FILE: cmfs/cmfs_backend/auth_app/urls.py
ACTION: REPLACE (Phase 4)
CHANGES:
  - All existing Phase 2/3 routes unchanged.
  - Note: user CRUD routes (invite, list, patch, delete, invalidate) are in
    api_urls.py, not here, so auth_app/urls.py remains auth-only.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('login/',                      views.LoginView.as_view(),               name='auth-login'),
    path('logout/',                     views.LogoutView.as_view(),              name='auth-logout'),
    path('refresh/',                    views.TokenRefreshView.as_view(),        name='auth-refresh'),
    path('me/',                         views.MeView.as_view(),                  name='auth-me'),

    # TOTP
    path('totp/setup/',                 views.TOTPSetupView.as_view(),           name='totp-setup'),
    path('totp/confirm/',               views.TOTPConfirmView.as_view(),         name='totp-confirm'),
    path('totp/verify-login/',          views.TOTPVerifyLoginView.as_view(),     name='totp-verify-login'),
    path('totp/recovery/',              views.TOTPRecoveryLoginView.as_view(),   name='totp-recovery'),
    path('totp/admin-reset/',           views.AdminTOTPResetView.as_view(),      name='totp-admin-reset'),

    # Account setup + password reset
    path('setup/totp-init/',            views.AccountSetupTOTPInitView.as_view(), name='account-setup-totp-init'),
    path('setup/',                      views.AccountSetupView.as_view(),        name='account-setup'),
    path('password-reset/request/',     views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/',     views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]