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
from django_q.tasks import async_task
from auth_app.audit import log
from auth_app.permissions import (
    IsSuperAdmin, IsAuthenticated, IsCountyHeadOrAbove,
    can_invite_role, get_invitable_roles,
)
import jwt


# ── helpers ────────────────────────────────────────────────────────────────────

REFRESH_COOKIE = 'refresh_token'
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


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


def _issue_tokens(user, response_data: dict, response):
    access = generate_access_token(user)
    refresh = generate_refresh_token(user)
    response_data['access_token'] = access
    _set_refresh_cookie(response, refresh)
    return access


def _user_dict(u: User) -> dict:
    return {
        'id': u.id,
        'full_name': u.full_name,
        'email': u.email,
        'phone': u.phone,
        'role': u.role,
        'county_id': u.county_id,
        'region_id': u.region_id,
        'totp_enabled': u.totp_enabled,
        'last_login_at': u.last_login_at.isoformat() if u.last_login_at else None,
        'last_login_ip': u.last_login_ip,
        'created_at': u.created_at.isoformat() if u.created_at else None,
        'status': _user_status(u),
    }


def _user_status(u: User) -> str:
    if u.setup_token and u.setup_token_expires_at and u.setup_token_expires_at > dj_tz.now():
        if not u.password_hash:
            return 'pending_setup'
    if u.locked_until and u.locked_until > dj_tz.now():
        return 'locked'
    return 'active'


# ── Login ──────────────────────────────────────────────────────────────────────

@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='post')
class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { email, password }
    Returns access token + sets HttpOnly refresh cookie.
    For TOTP users returns { requires_totp: true, partial_token }.
    """
    permission_classes = []

    def post(self, request):
        ip = get_client_ip(request)
        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''

        if not email or not password:
            return Response(
                {'error': 'Email and password are required.', 'code': 'missing_credentials'},
                status=400,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            log(action='login_failed', detail=f'No user: {email}', ip=ip)
            return Response(
                {'error': 'Invalid email or password.', 'code': 'invalid_credentials'},
                status=401,
            )

        if user.locked_until and user.locked_until > dj_tz.now():
            return Response(
                {'error': 'Account locked for 30 minutes due to too many failed attempts.', 'code': 'account_locked'},
                status=429,
            )

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = dj_tz.now() + timedelta(minutes=30)
                user.failed_login_attempts = 0
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
            log(user=user, action='login_failed', detail='Wrong password', ip=ip)
            return Response(
                {'error': 'Invalid email or password.', 'code': 'invalid_credentials'},
                status=401,
            )

        user.failed_login_attempts = 0
        user.last_login_at = dj_tz.now()
        user.last_login_ip = ip
        user.save(update_fields=['failed_login_attempts', 'last_login_at', 'last_login_ip'])

        totp_roles = {'super_admin', 'national_head', 'regional_head', 'county_head', 'budget_creator'}
        if user.role in totp_roles and user.totp_enabled:
            partial_token = generate_access_token(user)
            log(user=user, action='login_partial_totp', detail='TOTP step pending', ip=ip)
            return Response({'requires_totp': True, 'partial_token': partial_token})

        response = Response({})
        _issue_tokens(user, response.data, response)
        response.data['user'] = _user_dict(user)
        log(user=user, action='login_success', detail='', ip=ip)
        return response


# ── Token Refresh ──────────────────────────────────────────────────────────────

class TokenRefreshView(APIView):
    """POST /api/auth/refresh/"""
    permission_classes = []

    def post(self, request):
        token = request.COOKIES.get(REFRESH_COOKIE)
        if not token:
            return Response({'error': 'No refresh token.', 'code': 'no_token'}, status=401)

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Refresh token expired.', 'code': 'token_expired'}, status=401)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid token.', 'code': 'invalid_token'}, status=401)

        if payload.get('type') != 'refresh':
            return Response({'error': 'Wrong token type.', 'code': 'wrong_type'}, status=401)

        try:
            user = User.objects.get(pk=payload['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=401)

        if user.token_version != payload.get('token_version'):
            return Response({'error': 'Session invalidated.', 'code': 'session_invalid'}, status=401)

        access = generate_access_token(user)
        return Response({'access_token': access})


# ── Logout ─────────────────────────────────────────────────────────────────────

@method_decorator(ratelimit(key='ip', rate='60/m', method='POST', block=True), name='post')
class LogoutView(APIView):
    """POST /api/auth/logout/"""
    permission_classes = []

    def post(self, request):
        response = Response({'message': 'Logged out.'})
        _clear_refresh_cookie(response)
        return response


# ── TOTP ───────────────────────────────────────────────────────────────────────

class TOTPSetupView(APIView):
    """POST /api/auth/totp/setup/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.auth_user
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, user.email)
        qr_data_uri = get_totp_qr_data_uri(secret, user.email)

        user.totp_secret = secret
        user.totp_enabled = False
        user.save(update_fields=['totp_secret', 'totp_enabled'])

        log(user=user, action='totp_setup_initiated', ip=get_client_ip(request))
        return Response({'qr_data_uri': qr_data_uri, 'totp_uri': uri, 'secret': secret})


class TOTPConfirmView(APIView):
    """POST /api/auth/totp/confirm/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.auth_user
        code = request.data.get('code', '')

        if not user.totp_secret:
            return Response({'error': 'TOTP not set up yet.', 'code': 'totp_not_setup'}, status=400)

        if not verify_totp_code(user.totp_secret, code):
            return Response({'error': 'Invalid code.', 'code': 'invalid_totp'}, status=400)

        user.totp_enabled = True
        user.save(update_fields=['totp_enabled'])

        RecoveryCode.objects.filter(user=user).delete()
        plain_codes = generate_recovery_codes(8)
        for plain in plain_codes:
            RecoveryCode.objects.create(user=user, code_hash=hash_recovery_code(plain))

        log(user=user, action='totp_enabled', ip=get_client_ip(request))
        return Response({
            'recovery_codes': plain_codes,
            'message': 'TOTP enabled. Store these recovery codes safely — shown once only.',
        })


@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='post')
class TOTPVerifyLoginView(APIView):
    """POST /api/auth/totp/verify-login/"""
    permission_classes = []

    def post(self, request):
        ip = get_client_ip(request)
        partial_token = request.data.get('partial_token', '')
        code = request.data.get('code', '')

        try:
            payload = decode_token(partial_token)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid or expired partial token.', 'code': 'invalid_token'}, status=401)

        try:
            user = User.objects.get(pk=payload['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=401)

        if not verify_totp_code(user.totp_secret, code):
            log(user=user, action='totp_login_failed', ip=ip)
            return Response({'error': 'Invalid TOTP code.', 'code': 'invalid_totp'}, status=401)

        response = Response({})
        _issue_tokens(user, response.data, response)
        response.data['user'] = _user_dict(user)
        log(user=user, action='login_success', detail='via TOTP', ip=ip)
        return response


class TOTPRecoveryLoginView(APIView):
    """POST /api/auth/totp/recovery/"""
    permission_classes = []

    def post(self, request):
        ip = get_client_ip(request)
        partial_token = request.data.get('partial_token', '')
        recovery_code = request.data.get('recovery_code', '')

        try:
            payload = decode_token(partial_token)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid partial token.', 'code': 'invalid_token'}, status=401)

        try:
            user = User.objects.get(pk=payload['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=401)

        unused_codes = RecoveryCode.objects.filter(user=user, used=False)
        matched = None
        for rc in unused_codes:
            if verify_recovery_code(recovery_code, rc.code_hash):
                matched = rc
                break

        if not matched:
            log(user=user, action='recovery_code_failed', ip=ip)
            return Response({'error': 'Recovery code already used or invalid.', 'code': 'invalid_recovery_code'}, status=401)

        matched.used = True
        matched.used_at = dj_tz.now()
        matched.save(update_fields=['used', 'used_at'])

        response = Response({})
        _issue_tokens(user, response.data, response)
        response.data['user'] = _user_dict(user)
        log(user=user, action='login_success', detail='via recovery code', ip=ip)
        return response


class AdminTOTPResetView(APIView):
    """POST /api/auth/totp/admin-reset/"""
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        ip = get_client_ip(request)
        admin = request.auth_user
        target_id = request.data.get('user_id')
        totp_code = request.data.get('totp_code', '')

        if not verify_totp_code(admin.totp_secret, totp_code):
            return Response({'error': 'Your TOTP code is invalid.', 'code': 'invalid_totp'}, status=403)

        try:
            target = User.objects.get(pk=target_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=404)

        target.totp_secret = ''
        target.totp_enabled = False
        target.token_version += 1

        setup_token = generate_setup_token()
        target.setup_token = setup_token
        target.setup_token_expires_at = dj_tz.now() + timedelta(hours=48)
        target.save(update_fields=[
            'totp_secret', 'totp_enabled', 'token_version',
            'setup_token', 'setup_token_expires_at',
        ])

        RecoveryCode.objects.filter(user=target).delete()

        async_task('auth_app.emails.send_invitation_email', target.id)
        log(user=admin, action='admin_totp_reset', detail=f'Reset TOTP for user id={target.id}', ip=ip)
        return Response({'message': f'TOTP reset for {target.full_name}. New setup email sent.'})


# ── Account Setup ──────────────────────────────────────────────────────────────

class AccountSetupTOTPInitView(APIView):
    """
    POST /api/auth/setup/totp-init/
    Body: { token }

    Generates the TOTP secret + QR code for a brand-new invited user, before
    they have a password or any JWT. Identifies the user by their one-time
    setup_token (same one from the invitation email/link) instead of
    IsAuthenticated — a new user cannot possibly hold a valid JWT yet, so the
    normal /api/auth/totp/setup/ endpoint isn't reachable at this point in
    the flow. Call this first, then finish with POST /api/auth/setup/.
    """
    permission_classes = []

    def post(self, request):
        token = request.data.get('token', '')
        if not token:
            return Response({'error': 'Setup token is required.', 'code': 'missing_token'}, status=400)

        try:
            user = User.objects.get(setup_token=token)
        except User.DoesNotExist:
            return Response({'error': 'Setup link already used or expired.', 'code': 'invalid_setup_token'}, status=400)

        if not user.setup_token_expires_at or user.setup_token_expires_at < dj_tz.now():
            return Response({'error': 'Setup link already used or expired.', 'code': 'invalid_setup_token'}, status=400)

        secret = generate_totp_secret()
        uri = get_totp_uri(secret, user.email)
        qr_data_uri = get_totp_qr_data_uri(secret, user.email)

        user.totp_secret = secret
        user.totp_enabled = False
        user.save(update_fields=['totp_secret', 'totp_enabled'])

        log(user=user, action='totp_setup_initiated', ip=get_client_ip(request))
        return Response({'qr_data_uri': qr_data_uri, 'totp_uri': uri, 'secret': secret})


class AccountSetupView(APIView):
    """POST /api/auth/setup/"""
    permission_classes = []

    def post(self, request):
        token = request.data.get('token', '')
        password = request.data.get('password', '')
        totp_code = request.data.get('totp_code', '')

        if not token:
            return Response({'error': 'Setup token is required.', 'code': 'missing_token'}, status=400)

        try:
            user = User.objects.get(setup_token=token)
        except User.DoesNotExist:
            return Response({'error': 'Setup link already used or expired.', 'code': 'invalid_setup_token'}, status=400)

        if not user.setup_token_expires_at or user.setup_token_expires_at < dj_tz.now():
            return Response({'error': 'Setup link already used or expired.', 'code': 'invalid_setup_token'}, status=400)

        err = validate_password_strength(password)
        if err:
            return Response({'error': err, 'code': 'weak_password'}, status=400)

        if not user.totp_secret:
            return Response({'error': 'TOTP not configured. Call /api/auth/totp/setup/ first.', 'code': 'totp_not_setup'}, status=400)

        if not verify_totp_code(user.totp_secret, totp_code):
            return Response({'error': 'Invalid TOTP code.', 'code': 'invalid_totp'}, status=400)

        user.password_hash = hash_password(password)
        user.totp_enabled = True
        user.setup_token = ''
        user.setup_token_expires_at = None
        user.save(update_fields=['password_hash', 'totp_enabled', 'setup_token', 'setup_token_expires_at'])

        RecoveryCode.objects.filter(user=user).delete()
        plain_codes = generate_recovery_codes(8)
        for plain in plain_codes:
            RecoveryCode.objects.create(user=user, code_hash=hash_recovery_code(plain))

        log(user=user, action='account_setup_complete', ip=get_client_ip(request))
        return Response({'message': 'Account set up successfully.', 'recovery_codes': plain_codes})


# ── Password Reset ─────────────────────────────────────────────────────────────

@method_decorator(ratelimit(key='ip', rate='3/m', method='POST', block=True), name='post')
class PasswordResetRequestView(APIView):
    """POST /api/auth/password-reset/request/"""
    permission_classes = []

    def post(self, request):
        ip = get_client_ip(request)
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response({'error': 'Email is required.', 'code': 'missing_email'}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'If that email is registered, a reset link has been sent.'})

        reset_token = generate_setup_token()
        user.setup_token = reset_token
        user.setup_token_expires_at = dj_tz.now() + timedelta(hours=1)
        user.save(update_fields=['setup_token', 'setup_token_expires_at'])


        async_task('auth_app.emails.send_password_reset_email', user.id)
        log(user=user, action='password_reset_requested', ip=ip)
        return Response({'message': 'If that email is registered, a reset link has been sent.'})


@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='post')
class PasswordResetConfirmView(APIView):
    """POST /api/auth/password-reset/confirm/"""
    permission_classes = []

    def post(self, request):
        ip = get_client_ip(request)
        token = request.data.get('token', '')
        password = request.data.get('password', '')

        if not token or not password:
            return Response({'error': 'Token and password are required.', 'code': 'missing_fields'}, status=400)

        try:
            user = User.objects.get(setup_token=token)
        except User.DoesNotExist:
            return Response({'error': 'Setup link already used or expired.', 'code': 'invalid_token'}, status=400)

        if not user.setup_token_expires_at or user.setup_token_expires_at < dj_tz.now():
            return Response({'error': 'Setup link already used or expired.', 'code': 'token_expired'}, status=400)

        err = validate_password_strength(password)
        if err:
            return Response({'error': err, 'code': 'weak_password'}, status=400)

        user.password_hash = hash_password(password)
        user.totp_secret = ''
        user.totp_enabled = False
        user.token_version += 1
        user.setup_token = ''
        user.setup_token_expires_at = None
        user.save(update_fields=[
            'password_hash', 'totp_secret', 'totp_enabled',
            'token_version', 'setup_token', 'setup_token_expires_at',
        ])

        RecoveryCode.objects.filter(user=user).delete()
        log(user=user, action='password_reset_complete', ip=ip)

        # Short-lived access token so the frontend can call the authenticated
        # /api/auth/totp/setup/ and /api/auth/totp/confirm/ endpoints right
        # away, without a full separate login step. Mirrors the partial_token
        # issued mid-login when TOTP verification is still pending.
        setup_access_token = generate_access_token(user)

        return Response({
            'message': 'Password reset. Please set up your authenticator app.',
            'totp_reset': True,
            'setup_access_token': setup_access_token,
        })


# ── User Management ────────────────────────────────────────────────────────────

class InviteUserView(APIView):
    """
    POST /api/users/invite/
    Body: { full_name, email, phone (opt), role }

    """
    permission_classes = [IsCountyHeadOrAbove]

    # Roles that require the caller to be anchored to a convention unit
    OPERATIONAL_ROLES = {'budget_creator', 'finance_viewer', 'gate_official'}

    def post(self, request):
        ip = get_client_ip(request)
        caller = request.auth_user
        data = request.data

        # ── Validate required fields ───────────────────────────────────────────
        for field in ['full_name', 'email', 'role']:
            if not data.get(field):
                return Response(
                    {'error': f'{field} is required.', 'code': 'missing_field'},
                    status=400,
                )

        target_role = data['role']
        email = data['email'].strip().lower()

        # ── Role hierarchy check ───────────────────────────────────────────────
        if not can_invite_role(caller.role, target_role):
            invitable = get_invitable_roles(caller.role)
            return Response({
                'error': (
                    f'Your role ({caller.role}) cannot invite {target_role}. '
                    f'You can invite: {", ".join(sorted(invitable)) or "nobody"}.'
                ),
                'code': 'forbidden_role',
            }, status=403)

        # ── Resolve scope fields based on caller role ──────────────────────────
        county_id = data.get('county_id')
        region_id = data.get('region_id')

        if caller.role == 'super_admin':
            # Super Admin: county_id/region_id passed through as-is,
            # but a head role MUST get its matching scope — otherwise the
            # head (and everyone they later invite, who inherits from them)
            # ends up unscoped and silently sees nothing.
            if target_role == 'regional_head' and not region_id:
                return Response({
                    'error': 'region_id is required when creating a regional_head.',
                    'code': 'missing_field',
                }, status=400)

            if target_role == 'county_head' and not county_id:
                return Response({
                    'error': 'county_id is required when creating a county_head.',
                    'code': 'missing_field',
                }, status=400)

            if region_id:
                from conventions.models import Region
                if not Region.objects.filter(pk=region_id).exists():
                    return Response({'error': 'Region not found.', 'code': 'not_found'}, status=400)

            if county_id:
                from conventions.models import County
                try:
                    county = County.objects.get(pk=county_id)
                except County.DoesNotExist:
                    return Response({'error': 'County not found.', 'code': 'not_found'}, status=400)
                # If both are supplied for a county_head, lock region to the
                # county's actual region rather than trusting two independent
                # form fields to agree with each other.
                if target_role == 'county_head':
                    region_id = county.region_id

        elif target_role in self.OPERATIONAL_ROLES:
            # ── Operational staff invited by any head role ─────────────────────
            # Scope is inherited entirely from the caller's own assignment.
            # Convention-unit assignment happens later, via convention creation.
            county_id = caller.county_id
            region_id = caller.region_id

        elif caller.role == 'regional_head':
            # ── Regional Head inviting a county_head ───────────────────────────
            # county_id is required and must belong to the caller's region.
            if not caller.region_id:
                return Response({
                    'error': 'Your account has no region assigned. Contact Super Admin.',
                    'code': 'no_scope',
                }, status=403)

            if not county_id:
                return Response({
                    'error': 'county_id is required when inviting a county_head.',
                    'code': 'missing_field',
                }, status=400)

            from conventions.models import County
            try:
                county = County.objects.get(pk=county_id)
            except County.DoesNotExist:
                return Response({'error': 'County not found.', 'code': 'not_found'}, status=400)

            if county.region_id != caller.region_id:
                return Response({
                    'error': 'That county is not within your region.',
                    'code': 'out_of_scope',
                }, status=403)

            # Lock region to caller's own — never trust the submitted value.
            region_id = caller.region_id

        elif caller.role == 'national_head':
            # ── National Head inviting a regional_head ─────────────────────────
            # region_id is optional but if supplied must exist.
            if region_id:
                from conventions.models import Region
                if not Region.objects.filter(pk=region_id).exists():
                    return Response({'error': 'Region not found.', 'code': 'not_found'}, status=400)

        # ── Duplicate email check ──────────────────────────────────────────────
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'A user with this email already exists.', 'code': 'duplicate_email'},
                status=400,
            )

        # ── Create user + send invite ──────────────────────────────────────────
        setup_token = generate_setup_token()

        user = User.objects.create(
            full_name=data['full_name'].strip(),
            email=email,
            phone=data.get('phone', ''),
            role=target_role,
            county_id=county_id,
            region_id=region_id,
            password_hash='',
            setup_token=setup_token,
            setup_token_expires_at=dj_tz.now() + timedelta(hours=48),
        )

        setup_url = f"{settings.FRONTEND_URL}/auth/setup?token={setup_token}"
        async_task('auth_app.emails.send_invitation_email', user.id)
        log(
            user=caller,
            action='user_invited',
            detail=f'Invited {email} as {target_role} by {caller.role}',
            ip=ip,
        )

        return Response({
            'message': f'Invitation sent to {email}.',
            'user_id': user.id,
            'setup_url': setup_url,
        }, status=201)


class UserListView(APIView):
    """
    GET /api/users/
    Super Admin: all users.
    National Head: all users except other super admins.
    Regional Head: users in counties within their region.
    County Head: users in their county.

    Query params: ?role=  ?county_id=  ?region_id=  ?page=
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        caller = request.auth_user

        if caller.role not in ('super_admin', 'national_head', 'regional_head', 'county_head'):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        qs = User.objects.all().order_by('full_name')

        if caller.role == 'county_head':
            if not caller.county_id:
                return Response({
                    'error': 'Your account has no county assigned. Contact Super Admin.',
                    'code': 'no_scope',
                }, status=403)
            qs = qs.filter(county_id=caller.county_id)

        elif caller.role == 'regional_head':
            if not caller.region_id:
                return Response({
                    'error': 'Your account has no region assigned. Contact Super Admin.',
                    'code': 'no_scope',
                }, status=403)
            from conventions.models import County
            county_ids = list(
                County.objects.filter(region_id=caller.region_id).values_list('id', flat=True)
            )
            qs = qs.filter(county_id__in=county_ids)

        elif caller.role == 'national_head':
            qs = qs.exclude(role='super_admin')

        # Optional filters
        if role_filter := request.query_params.get('role'):
            qs = qs.filter(role=role_filter)
        if county_filter := request.query_params.get('county_id'):
            qs = qs.filter(county_id=county_filter)
        if region_filter := request.query_params.get('region_id'):
            qs = qs.filter(region_id=region_filter)

        # Pagination
        page = max(1, int(request.query_params.get('page', 1)))
        page_size = 50
        offset = (page - 1) * page_size
        total = qs.count()
        users = qs[offset:offset + page_size]

        return Response({
            'users': [_user_dict(u) for u in users],
            'total': total,
            'page': page,
            'page_size': page_size,
        })


class PatchUserView(APIView):
    """
    PATCH /api/users/<id>/
    Super Admin only — update non-sensitive fields.
    """
    permission_classes = [IsSuperAdmin]

    def patch(self, request, user_id):
        ip = get_client_ip(request)
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=404)

        allowed_fields = ['full_name', 'phone', 'role', 'county_id', 'region_id']
        updated = []
        for field in allowed_fields:
            if field in request.data:
                setattr(target, field, request.data[field])
                updated.append(field)

        if not updated:
            return Response({'error': 'No updatable fields provided.', 'code': 'no_changes'}, status=400)

        target.save(update_fields=updated)
        log(
            user=request.auth_user,
            action='user_updated',
            detail=f'Updated {updated} for user id={target.id}',
            ip=ip,
        )
        return Response({'user': _user_dict(target)})


class DeleteUserView(APIView):
    """
    DELETE /api/users/<id>/
    Super Admin only. Cannot delete yourself.
    """
    permission_classes = [IsSuperAdmin]

    def delete(self, request, user_id):
        ip = get_client_ip(request)
        if request.auth_user.id == int(user_id):
            return Response({'error': 'You cannot delete your own account.', 'code': 'self_delete'}, status=400)

        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.', 'code': 'not_found'}, status=404)

        name = target.full_name
        target.delete()
        log(
            user=request.auth_user,
            action='user_deleted',
            detail=f'Deleted user {name} id={user_id}',
            ip=ip,
        )
        return Response({'message': f'User {name} deleted.'}, status=200)


class InvalidateSessionsView(APIView):
    """
    POST /api/users/<id>/invalidate-sessions/
    Super Admin only.
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
        log(
            user=request.auth_user,
            action='sessions_invalidated',
            detail=f'All sessions killed for user id={target.id}',
            ip=ip,
        )
        return Response({'message': f'All sessions for {target.full_name} have been invalidated.'})


class MeView(APIView):
    """GET /api/auth/me/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'user': _user_dict(request.auth_user)})