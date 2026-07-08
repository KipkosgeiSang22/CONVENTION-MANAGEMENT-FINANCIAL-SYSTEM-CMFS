"""
FILE: cmfs/cmfs_backend/payments/hmac_utils.py
ACTION: CREATE (Phase 6)

Security Section 9 requires HMAC-SHA256 verification on the M-Pesa
callback as a second layer, on top of IP whitelisting. Safaricom's Daraja
API does not natively sign callbacks, so this assumes the callback is
routed through a gateway/proxy (or Safaricom's newer signed-webhook
config, where available) that adds an `X-Mpesa-Signature` header
computed the same way. Change HEADER_NAME below if your gateway uses a
different header.
"""

import hmac
import hashlib

from django.conf import settings

HEADER_NAME = 'HTTP_X_MPESA_SIGNATURE'


def verify_callback_hmac(request) -> bool:
    """
    Recomputes HMAC-SHA256 of the raw request body using
    MPESA_CALLBACK_HMAC_SECRET and compares it (constant-time) against
    the signature header. Returns False if the header is missing or
    doesn't match.
    """
    secret = getattr(settings, 'MPESA_CALLBACK_HMAC_SECRET', '') or ''
    if not secret:
        return False

    signature = request.META.get(HEADER_NAME, '')
    if not signature:
        return False

    expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)