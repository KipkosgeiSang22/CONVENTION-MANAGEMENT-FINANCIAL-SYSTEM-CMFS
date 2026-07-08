import jwt
import bcrypt
import pyotp
import qrcode
import io
import base64
import secrets
import string
from datetime import datetime, timedelta, timezone
from django.conf import settings


# ── JWT ────────────────────────────────────────────────────────────────────────

def generate_access_token(user):
    """Issue a 15-minute access token."""
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user.id,
        'full_name': user.full_name,
        'county_id': user.county_id,
        'region_id': user.region_id,
        'role': user.role,
        'token_version': user.token_version,
        'iat': now,
        'exp': now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRY_MINUTES),
        'type': 'access',
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')


def generate_refresh_token(user):
    """Issue a 7-day refresh token."""
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user.id,
        'token_version': user.token_version,
        'iat': now,
        'exp': now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRY_DAYS),
        'type': 'refresh',
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')


def decode_token(token):
    """
    Decode and verify a JWT.
    Returns the payload dict, or raises jwt.InvalidTokenError.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])


# ── Password ───────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def validate_password_strength(password: str):
    """
    Returns None if valid, or a string describing the problem.
    Rules: min 8 chars, at least one digit, at least one symbol.
    """
    if len(password) < 8:
        return 'Password must be at least 8 characters.'
    if not any(c.isdigit() for c in password):
        return 'Password must contain at least one number.'
    symbols = set(string.punctuation)
    if not any(c in symbols for c in password):
        return 'Password must contain at least one symbol.'
    return None


# ── TOTP ───────────────────────────────────────────────────────────────────────

TOTP_ISSUER = 'KSCF Convention System'


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=TOTP_ISSUER,
    )


def verify_totp_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def get_totp_qr_data_uri(secret: str, email: str) -> str:
    """Return a base64-encoded PNG data URI for the QR code."""
    uri = get_totp_uri(secret, email)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f'data:image/png;base64,{b64}'


# ── Recovery codes ─────────────────────────────────────────────────────────────

def generate_recovery_codes(count=8) -> list[str]:
    """Return a list of plain recovery codes (shown once only)."""
    alphabet = string.ascii_uppercase + string.digits
    return [''.join(secrets.choice(alphabet) for _ in range(10)) for _ in range(count)]


def hash_recovery_code(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_recovery_code(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Setup / reset tokens ───────────────────────────────────────────────────────

def generate_setup_token() -> str:
    return secrets.token_urlsafe(64)


def get_client_ip(request) -> str:
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# ── Phone normalisation (Phase 6) ───────────────────────────────────────────────

import re as _re


def normalize_kenyan_phone(raw: str):
    """
    Accepts 07XXXXXXXX, 01XXXXXXXX, +2547XXXXXXXX, 2547XXXXXXXX (and the
    01-prefixed equivalents) and normalises to 2547XXXXXXXX / 2541XXXXXXXX.
    Returns the normalised string, or None if the input isn't a valid
    Kenyan mobile number.
    """
    if not raw:
        return None
    p = raw.strip().replace(' ', '').replace('-', '')
    if p.startswith('+'):
        p = p[1:]

    if p.startswith('0') and len(p) == 10 and p[1] in ('7', '1'):
        p = '254' + p[1:]

    if _re.match(r'^254[17]\d{8}$', p):
        return p
    return None