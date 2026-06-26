import jwt
from django.conf import settings
from django.http import JsonResponse
from auth_app.models import User


class JWTAuthMiddleware:
    """
    Extracts and validates the Bearer JWT on every request.
    Sets `request.user_payload` (the decoded token dict) and
    `request.auth_user` (the User ORM instance) when valid.
    Both are None when the request carries no/invalid token.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user_payload = None
        request.auth_user = None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                from auth_app.utils import decode_token
                payload = decode_token(token)

                if payload.get('type') != 'access':
                    return self._unauth('Invalid token type.')

                # token_version check — invalidates all old sessions
                user_id = payload.get('user_id')
                try:
                    user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    return self._unauth('User not found.')

                if user.token_version != payload.get('token_version'):
                    return self._unauth('Session invalidated. Please log in again.')

                request.user_payload = payload
                request.auth_user = user

            except jwt.ExpiredSignatureError:
                return self._unauth('Access token expired.')
            except jwt.InvalidTokenError:
                return self._unauth('Invalid access token.')

        return self.get_response(request)

    @staticmethod
    def _unauth(message):
        return JsonResponse({'error': message, 'code': 'unauthorized'}, status=401)