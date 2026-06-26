import secrets
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.utils import timezone as dj_tz
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from auth_app.models import User, RecoveryCode
from auth_app.utils import (
    verify_password, hash_password, validate_password_strength,
    generate_access_token, generate_refresh_token, decode_token,
    generate_totp_secret, get_totp_uri, get_totp_qr_data_uri,
    verify_totp_code,
    generate_recovery_codes, hash_recovery_code, verify_recovery_code,
    generate_setup_token, get_client_ip,
)
from auth_app.emails import send_invitation_email, send_password_reset_email
from auth_app.audit import log
from auth_app.permissions import IsSuperAdmin, IsAuthenticated
import jwt


# ── helpers ────────────────────────────────────────────────────────────────────

REFRESH_COOKIE = 'refresh_token'
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds


def _set_refresh_cookie(response, token: str):
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite='Lax',
        secure=not settings.DEBUG,
    )


def _clear_refresh_cookie(response):
    response.delete_cookie(REFRESH_COOKIE)


def _issue_tokens(user, response_data: dict, response: Response):
    access = generate_access_token(user)
    refresh = generate_refresh_token(user)
    response_data['access_token'] = access
    _set_refresh_cookie(response, refresh)
    return response


# ── Login ──────────────────────────────────────────────────────────────────────

@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='post')
class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { email, password }

    Returns:
      - If TOTP enabled: { requires_totp: true, partial_token: <short-lived token> }
      - If no TOTP:      { access_token, user: {...} } + HttpOnly refresh cookie
    """

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        ip = get_client_ip(request)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials.', 'code': 'invalid_credentials'}, status=401)

        # Lockout check
        if user.locked_until and dj_tz.now() < user.locked_until:
            remaining = int((user.locked_until - dj_tz.now()).total_seconds() / 60) + 1
            return Response(
                {'error': f'Account locked for {remaining} more minute(s).', 'code': 'account_locked'},
                status=429
            )

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = dj_tz.now() + timedelta(minutes=30)
                log(user=user, action='account_locked', detail='5 failed login attempts', ip=ip)
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
            log(user=user, action='login_failure', detail='Wrong password', ip=ip)
            return Response({'error': 'Invalid credentials.', 'code': 'invalid_credentials'}, status=401)

        # Reset failure counter
        user.failed_login_attempts = 0
        user.locked_until = None

        if user.totp_enabled:
            # Issue a short-lived partial token (1 minute) for the TOTP step
            partial_token = generate_access_token.__wrapped__(user) if hasattr(generate_access_token, '__wrapped__') else _partial_token(user)
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
            return Response({'requires_totp': True, 'partial_token': partial_token})

        # No TOTP — full login
        user.last_login_at = dj_tz.now()
        user.last_login_ip = ip
        user.save(update_fields=['failed_login_attempts', 'locked_until', 'last_login_at', 'last_login_ip'])
        log(user=user, action='login_success', detail='No TOTP', ip=ip)

        resp = Response({
            'user': _user_dict(user),
        })
        return _issue_tokens(user, resp.data, resp)


def _partial_token(user):
    """Very short-lived token used only during TOTP step."""
    import jwt as _jwt
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user.id,
        'token_version': user.token_version,
        'iat': now,
        'exp': now + timedelta(minutes=5),
        'type': 'partial',
    }
    return _jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')


def _user_dict(user):
    return {
        'id': user.id,
        'full_name': user.full_name,
        'email': user.email,
        'role': user.role,
        'county_id': user.county_id,
        'region_id': user.region_id,
        'convention_unit_id': user.convention_unit_id,
        'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
        'last_login_ip': user.last_login_ip,
        'totp_enabled': user.totp_enabled,
    }


# ── TOTP verify (post-login step) ──────────────────────────────────────────────

@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='post')
class TOTPVerifyLoginView(APIView):
    """
    POST /api/auth/totp/verify-login/
    Body: { partial_token, code }
    Completes login for TOTP-enabled users.
    """

    def post(self, request):
        partial_token = request.data.get('partial_token', '')
        code = request.data.get('code', '').strip()
        ip = get_client_ip(request)

        try:
            payload = decode_token(partial_token)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid or expired session.', 'code': 'invalid_token'}, status=401)

        if payload.get('type') != 'partial':
            return Response({'error': 'Invalid token type.', 'code': 'invalid_token'}, status=401)

        try:
            user = User.objects.get(pk=payload['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=404)

        if not verify_totp_code(user.totp_secret, code):
            log(user=user, action='totp_failure', detail='Wrong TOTP code at login', ip=ip)
            return Response({'error': 'Invalid TOTP code.', 'code': 'invalid_totp'}, status=401)

        user.last_login_at = dj_tz.now()
        user.last_login_ip = ip
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['last_login_at', 'last_login_ip', 'failed_login_attempts', 'locked_until'])
        log(user=user, action='login_success', detail='TOTP verified', ip=ip)

        resp = Response({'user': _user_dict(user)})
        return _issue_tokens(user, resp.data, resp)


# ── TOTP recovery code login ────────────────────────────────────────────────────

@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='post')
class TOTPRecoveryLoginView(APIView):
    """
    POST /api/auth/totp/recovery/
    Body: { partial_token, recovery_code }
    """

    def post(self, request):
        partial_token = request.data.get('partial_token', '')
        plain_code = request.data.get('recovery_code', '').strip().upper()
        ip = get_client_ip(request)

        try:
            payload = decode_token(partial_token)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid or expired session.', 'code': 'invalid_token'}, status=401)

        if payload.get('type') != 'partial':
            return Response({'error': 'Invalid token type.', 'code': 'invalid_token'}, status=401)

        try:
            user = User.objects.get(pk=payload['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=404)

        unused_codes = RecoveryCode.objects.filter(user=user, used=False)
        matched = None
        for rc in unused_codes:
            if verify_recovery_code(plain_code, rc.code_hash):
                matched = rc
                break

        if not matched:
            log(user=user, action='recovery_code_failure', detail='No matching unused code', ip=ip)
            return Response({'error': 'Recovery code already used or invalid.', 'code': 'invalid_recovery_code'}, status=401)

        matched.used = True
        matched.used_at = dj_tz.now()
        matched.save(update_fields=['used', 'used_at'])

        user.last_login_at = dj_tz.now()
        user.last_login_ip = ip
        user.save(update_fields=['last_login_at', 'last_login_ip'])
        log(user=user, action='recovery_code_used', detail=f'Recovery code id={matched.id} used', ip=ip)

        resp = Response({'user': _user_dict(user)})
        return _issue_tokens(user, resp.data, resp)


# ── Refresh ────────────────────────────────────────────────────────────────────

class TokenRefreshView(APIView):
    """
    POST /api/auth/refresh/
    Reads the HttpOnly refresh cookie, issues a new access token.
    """

    def post(self, request):
        token = request.COOKIES.get(REFRESH_COOKIE)
        if not token:
            return Response({'error': 'No refresh token.', 'code': 'no_refresh_token'}, status=401)

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Refresh token expired.', 'code': 'expired'}, status=401)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid refresh token.', 'code': 'invalid_token'}, status=401)

        if payload.get('type') != 'refresh':
            return Response({'error': 'Invalid token type.', 'code': 'invalid_token'}, status=401)

        try:
            user = User.objects.get(pk=payload['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=404)

        if user.token_version != payload.get('token_version'):
            return Response({'error': 'Session invalidated.', 'code': 'session_invalidated'}, status=401)

        access = generate_access_token(user)
        return Response({'access_token': access})


# ── Logout ─────────────────────────────────────────────────────────────────────

class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Clears the refresh cookie and logs the event.
    """

    def post(self, request):
        ip = get_client_ip(request)
        user = request.auth_user
        if user:
            log(user=user, action='logout', ip=ip)
        resp = Response({'message': 'Logged out.'})
        _clear_refresh_cookie(resp)
        return resp


# ── TOTP setup ──────────────────────────────────────────────────────────────────

class TOTPSetupView(APIView):
    """
    POST /api/auth/totp/setup/
    Generates a new TOTP secret and 8 recovery codes.
    Returns: { totp_uri, qr_data_uri, recovery_codes }
    Recovery codes shown ONCE only.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.auth_user
        ip = get_client_ip(request)

        secret = generate_totp_secret()
        plain_codes = generate_recovery_codes(8)

        # Persist secret (not yet enabled — enabled on verify)
        user.totp_secret = secret
        user.save(update_fields=['totp_secret'])

        # Replace all existing recovery codes
        RecoveryCode.objects.filter(user=user).delete()
        RecoveryCode.objects.bulk_create([
            RecoveryCode(user=user, code_hash=hash_recovery_code(c))
            for c in plain_codes
        ])

        log(user=user, action='totp_setup_initiated', ip=ip)

        return Response({
            'totp_uri': get_totp_uri(secret, user.email),
            'qr_data_uri': get_totp_qr_data_uri(secret, user.email),
            'recovery_codes': plain_codes,
        })


class TOTPConfirmView(APIView):
    """
    POST /api/auth/totp/confirm/
    Body: { code }
    Verifies the first TOTP code and marks TOTP as enabled.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.auth_user
        code = request.data.get('code', '').strip()
        ip = get_client_ip(request)

        if not user.totp_secret:
            return Response({'error': 'TOTP setup not initiated.', 'code': 'no_totp_secret'}, status=400)

        if not verify_totp_code(user.totp_secret, code):
            return Response({'error': 'Invalid TOTP code.', 'code': 'invalid_totp'}, status=400)

        user.totp_enabled = True
        user.save(update_fields=['totp_enabled'])
        log(user=user, action='totp_enabled', ip=ip)

        return Response({'message': 'TOTP enabled successfully.'})


# ── Account setup (invite link) ────────────────────────────────────────────────

class AccountSetupView(APIView):
    """
    POST /api/auth/setup/
    Body: { token, password, totp_code }
    One-time invite link: sets password + confirms TOTP.
    """

    def post(self, request):
        token = request.data.get('token', '').strip()
        password = request.data.get('password', '')
        totp_code = request.data.get('totp_code', '').strip()
        ip = get_client_ip(request)

        try:
            user = User.objects.get(setup_token=token)
        except User.DoesNotExist:
            return Response({'error': 'Invalid or expired setup link.', 'code': 'invalid_token'}, status=400)

        if not user.setup_token_expires_at or dj_tz.now() > user.setup_token_expires_at:
            return Response({'error': 'Setup link has expired.', 'code': 'token_expired'}, status=400)

        err = validate_password_strength(password)
        if err:
            return Response({'error': err, 'code': 'weak_password'}, status=400)

        if not user.totp_secret:
            return Response({'error': 'TOTP not yet configured. Call /api/auth/totp/setup/ first.', 'code': 'no_totp_secret'}, status=400)

        if not verify_totp_code(user.totp_secret, totp_code):
            return Response({'error': 'Invalid TOTP code.', 'code': 'invalid_totp'}, status=400)

        user.password_hash = hash_password(password)
        user.totp_enabled = True
        user.setup_token = ''
        user.setup_token_expires_at = None
        user.token_version += 1
        user.save(update_fields=['password_hash', 'totp_enabled', 'setup_token', 'setup_token_expires_at', 'token_version'])
        log(user=user, action='account_setup_complete', ip=ip)

        return Response({'message': 'Account set up successfully. Please log in.'})


# ── Password reset ─────────────────────────────────────────────────────────────

@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='post')
class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/request/
    Body: { email }
    Sends a 1-hour reset link.
    """

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        # Always respond 200 to prevent email enumeration
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'If that email exists, a reset link has been sent.'})

        token = generate_setup_token()
        user.setup_token = token
        user.setup_token_expires_at = dj_tz.now() + timedelta(hours=1)
        user.save(update_fields=['setup_token', 'setup_token_expires_at'])

        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
        send_password_reset_email(user, reset_url)
        log(user=user, action='password_reset_requested', ip=get_client_ip(request))

        return Response({'message': 'If that email exists, a reset link has been sent.'})


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password-reset/confirm/
    Body: { token, password, totp_code }
    Sets new password and re-enables TOTP.
    Invalidates all sessions by incrementing token_version.
    """

    def post(self, request):
        token = request.data.get('token', '').strip()
        password = request.data.get('password', '')
        totp_code = request.data.get('totp_code', '').strip()
        ip = get_client_ip(request)

        try:
            user = User.objects.get(setup_token=token)
        except User.DoesNotExist:
            return Response({'error': 'Invalid or expired reset link.', 'code': 'invalid_token'}, status=400)

        if not user.setup_token_expires_at or dj_tz.now() > user.setup_token_expires_at:
            return Response({'error': 'Reset link has expired.', 'code': 'token_expired'}, status=400)

        err = validate_password_strength(password)
        if err:
            return Response({'error': err, 'code': 'weak_password'}, status=400)

        if user.totp_secret and user.totp_enabled:
            if not verify_totp_code(user.totp_secret, totp_code):
                return Response({'error': 'Invalid TOTP code.', 'code': 'invalid_totp'}, status=400)

        user.password_hash = hash_password(password)
        user.setup_token = ''
        user.setup_token_expires_at = None
        user.token_version += 1   # invalidate all existing sessions
        user.save(update_fields=['password_hash', 'setup_token', 'setup_token_expires_at', 'token_version'])
        log(user=user, action='password_reset_complete', ip=ip)

        return Response({'message': 'Password reset successfully. Please log in.'})


# ── Super Admin: TOTP reset for any user ──────────────────────────────────────

class AdminTOTPResetView(APIView):
    """
    POST /api/auth/totp/admin-reset/
    Body: { target_user_id, totp_code }   ← admin's OWN totp_code
    Super Admin only. Clears the target user's TOTP and sends a new setup invite.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        admin = request.auth_user
        target_id = request.data.get('target_user_id')
        totp_code = request.data.get('totp_code', '').strip()
        ip = get_client_ip(request)

        if not verify_totp_code(admin.totp_secret, totp_code):
            return Response({'error': 'Invalid TOTP code.', 'code': 'invalid_totp'}, status=403)

        try:
            target = User.objects.get(pk=target_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=404)

        # Clear TOTP + recovery codes, increment token_version
        token = generate_setup_token()
        target.totp_secret = ''
        target.totp_enabled = False
        target.setup_token = token
        target.setup_token_expires_at = dj_tz.now() + timedelta(hours=48)
        target.token_version += 1
        target.save(update_fields=['totp_secret', 'totp_enabled', 'setup_token', 'setup_token_expires_at', 'token_version'])

        RecoveryCode.objects.filter(user=target).delete()

        setup_url = f"{settings.FRONTEND_URL}/auth/setup?token={token}"
        send_invitation_email(target, setup_url)
        log(user=admin, action='admin_totp_reset', detail=f'Reset TOTP for user id={target.id}', ip=ip)

        return Response({'message': f'TOTP reset for {target.full_name}. Setup invite sent.'})


# ── Invite user ────────────────────────────────────────────────────────────────

class InviteUserView(APIView):
    """
    POST /api/users/invite/
    Body: { full_name, email, phone, role, convention_unit_id, county_id, region_id }
    Super Admin only. Creates a user and sends a setup invite.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        ip = get_client_ip(request)
        data = request.data

        required = ['full_name', 'email', 'role']
        for field in required:
            if not data.get(field):
                return Response({'error': f'{field} is required.', 'code': 'missing_field'}, status=400)

        email = data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            return Response({'error': 'A user with this email already exists.', 'code': 'duplicate_email'}, status=400)

        token = generate_setup_token()

        user = User.objects.create(
            full_name=data['full_name'].strip(),
            email=email,
            phone=data.get('phone', ''),
            role=data['role'],
            convention_unit_id=data.get('convention_unit_id'),
            county_id=data.get('county_id'),
            region_id=data.get('region_id'),
            password_hash='',   # set during account setup
            setup_token=token,
            setup_token_expires_at=dj_tz.now() + timedelta(hours=48),
        )

        setup_url = f"{settings.FRONTEND_URL}/auth/setup?token={token}"
        send_invitation_email(user, setup_url)
        log(user=request.auth_user, action='user_invited', detail=f'Invited {email} as {data["role"]}', ip=ip)

        return Response({
            'message': f'Invitation sent to {email}.',
            'user_id': user.id,
        }, status=201)


# ── Session invalidation ────────────────────────────────────────────────────────

class InvalidateSessionsView(APIView):
    """
    POST /api/users/{id}/invalidate-sessions/
    Super Admin only. Increments token_version to kill all active sessions.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id):
        ip = get_client_ip(request)
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=404)

        target.token_version += 1
        target.save(update_fields=['token_version'])
        log(user=request.auth_user, action='sessions_invalidated', detail=f'All sessions killed for user id={target.id}', ip=ip)

        return Response({'message': f'All sessions for {target.full_name} have been invalidated.'})


# ── Me (current user info) ──────────────────────────────────────────────────────

class MeView(APIView):
    """
    GET /api/auth/me/
    Returns the current authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'user': _user_dict(request.auth_user)})