"""
FILE: cmfs/cmfs_backend/payments/middleware.py
ACTION: CREATE (Phase 6)

Security Section 9: the M-Pesa callback endpoint MUST reject any request
not originating from a whitelisted Safaricom IP, before any view code
runs. Checked here in middleware rather than in the view.
"""

from django.http import JsonResponse
from django.conf import settings

from auth_app.utils import get_client_ip

CALLBACK_PATH = '/api/payments/mpesa/callback/'


class MpesaIPWhitelistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == CALLBACK_PATH:
            ip = get_client_ip(request)
            whitelist = getattr(settings, 'MPESA_IP_WHITELIST', [])
            if ip not in whitelist:
                return JsonResponse(
                    {'error': 'Forbidden: source IP not whitelisted.', 'code': 'forbidden'},
                    status=403,
                )
        return self.get_response(request)