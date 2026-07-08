"""
FILE: cmfs/cmfs_backend/payments/daraja.py
ACTION: CREATE (Phase 6)

Minimal Safaricom Daraja (M-Pesa) client: OAuth token + STK Push.
Base URL defaults to the sandbox; set MPESA_BASE_URL in .env to
https://api.safaricom.co.ke for production.
"""

import base64
import logging
import time
from datetime import datetime

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = 'https://sandbox.safaricom.co.ke'

# Safaricom's sandbox sits behind Incapsula (a bot-protection WAF). Incapsula
# blocks the bare 'python-requests/x.y' User-Agent that the `requests`
# library sends by default — you get back an Incapsula HTML block page with
# HTTP 403 instead of ever reaching Daraja, regardless of whether your
# credentials are valid. Sending a normal browser-like User-Agent avoids
# that specific block *most* of the time, but Incapsula's bot-scoring is
# probabilistic, not a static blacklist — it can still trip intermittently
# even with a good User-Agent. Two mitigations below: (1) cache the OAuth
# token so we hit /oauth/v1/generate far less often (fewer requests =
# fewer chances to get flagged, and it's wasteful anyway — tokens are
# valid for ~1hr), and (2) transparently retry once if we do get blocked,
# since re-trying a moment later frequently succeeds.
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json',
}

_INCAPSULA_RETRY_DELAYS = (2, 5)  # seconds, between retry attempts


class DarajaError(Exception):
    pass


def _base_url() -> str:
    return getattr(settings, 'MPESA_BASE_URL', DEFAULT_BASE_URL)


def _looks_like_incapsula_block(resp) -> bool:
    return resp.status_code == 403 and 'Incapsula' in resp.text


# Module-level cache: (token, expires_at_epoch_seconds). Safaricom tokens
# are valid for ~3600s; we treat them as expired 5 minutes early to avoid
# racing the real expiry mid-request.
_token_cache = {'token': None, 'expires_at': 0}


def get_access_token(force_refresh: bool = False) -> str:
    """OAuth token via client_credentials grant, Basic-auth'd with consumer key/secret.

    Cached in-process for its lifetime to avoid hitting /oauth/v1/generate
    on every single STK Push / query call — both to reduce load on Daraja
    and to reduce how often we're exposed to Incapsula's bot-scoring.
    """
    now = time.time()
    if not force_refresh and _token_cache['token'] and now < _token_cache['expires_at']:
        return _token_cache['token']

    url = f'{_base_url()}/oauth/v1/generate?grant_type=client_credentials'
    last_exc = None
    for attempt, delay in enumerate((0, *_INCAPSULA_RETRY_DELAYS)):
        if delay:
            time.sleep(delay)
        resp = requests.get(
            url,
            auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
            headers=_HEADERS,
            timeout=15,
        )
        if resp.status_code == 200:
            token = resp.json()['access_token']
            _token_cache['token'] = token
            _token_cache['expires_at'] = now + 3300  # ~55 min, safely under the ~1hr expiry
            return token
        if _looks_like_incapsula_block(resp):
            logger.warning(
                'get_access_token: blocked by Incapsula (attempt %d/%d), retrying...',
                attempt + 1, len(_INCAPSULA_RETRY_DELAYS) + 1,
            )
            last_exc = DarajaError(f'Failed to obtain Daraja access token: {resp.status_code} (Incapsula block)')
            continue
        # A real Daraja-level rejection (bad credentials etc.) — no point retrying.
        raise DarajaError(f'Failed to obtain Daraja access token: {resp.status_code} {resp.text}')

    raise last_exc


def _password_and_timestamp():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw = f'{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}'
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


def initiate_stk_push(phone: str, amount, account_reference: str, transaction_desc: str) -> dict:
    """
    Sends the STK Push request. `phone` must already be normalised to
    2547XXXXXXXX. `account_reference` is the Delegate ID (or a temporary
    reference before the Delegate ID exists).

    Returns the parsed Daraja response dict on success (HTTP 200), which
    includes CheckoutRequestID / MerchantRequestID — the caller is
    responsible for storing CheckoutRequestID so the callback can be
    correlated back to the right Payment row.

    Raises DarajaError on any non-200 response or network failure.
    """
    token = get_access_token()
    password, timestamp = _password_and_timestamp()

    payload = {
        'BusinessShortCode': settings.MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': int(round(float(amount))),
        'PartyA': phone,
        'PartyB': settings.MPESA_SHORTCODE,
        'PhoneNumber': phone,
        'CallBackURL': settings.MPESA_CALLBACK_URL,
        'AccountReference': account_reference,
        'TransactionDesc': transaction_desc,
    }

    resp = None
    for attempt, delay in enumerate((0, *_INCAPSULA_RETRY_DELAYS)):
        if delay:
            time.sleep(delay)
        resp = requests.post(
            f'{_base_url()}/mpesa/stkpush/v1/processrequest',
            json=payload,
            headers={**_HEADERS, 'Authorization': f'Bearer {token}'},
            timeout=20,
        )
        if resp.status_code == 200 or not _looks_like_incapsula_block(resp):
            break
        logger.warning(
            'initiate_stk_push: blocked by Incapsula (attempt %d/%d), retrying...',
            attempt + 1, len(_INCAPSULA_RETRY_DELAYS) + 1,
        )

    if resp.status_code != 200:
        raise DarajaError(f'STK Push request failed: {resp.status_code} {resp.text}')

    data = resp.json()
    if str(data.get('ResponseCode')) != '0':
        raise DarajaError(f'STK Push rejected: {data}')

    return data


def query_stk_status(checkout_request_id: str) -> dict:
    """
    STK Push Query (/mpesa/stkpushquery/v1/query) — lets us actively ask
    Safaricom for the outcome of a transaction instead of waiting for
    their callback. Essential when the callback URL isn't publicly
    reachable (e.g. developing on a private network with no tunnel).

    Returns the parsed response dict, which includes a string
    'ResultCode' ('0' = success) and 'ResultDesc'. NOTE: unlike the
    callback, this does NOT include the M-Pesa receipt number or
    confirmed amount — only the callback carries that. If the
    transaction is still being processed, Safaricom responds with a
    non-200 / error payload; this raises DarajaError in that case so the
    caller can treat it as "still pending, try again shortly" rather
    than a failure.
    """
    token = get_access_token()
    password, timestamp = _password_and_timestamp()

    payload = {
        'BusinessShortCode': settings.MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'CheckoutRequestID': checkout_request_id,
    }

    resp = None
    for attempt, delay in enumerate((0, *_INCAPSULA_RETRY_DELAYS)):
        if delay:
            time.sleep(delay)
        resp = requests.post(
            f'{_base_url()}/mpesa/stkpushquery/v1/query',
            json=payload,
            headers={**_HEADERS, 'Authorization': f'Bearer {token}'},
            timeout=20,
        )
        if resp.status_code == 200 or not _looks_like_incapsula_block(resp):
            break
        logger.warning(
            'query_stk_status: blocked by Incapsula (attempt %d/%d), retrying...',
            attempt + 1, len(_INCAPSULA_RETRY_DELAYS) + 1,
        )

    if resp.status_code != 200:
        # Safaricom returns non-200 while the transaction is still being
        # processed, or if the CheckoutRequestID has expired/is unknown.
        raise DarajaError(f'STK Query not resolved yet: {resp.status_code} {resp.text}')

    return resp.json()