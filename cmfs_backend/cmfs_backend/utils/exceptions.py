from rest_framework.views import exception_handler
from rest_framework.response import Response
from django_ratelimit.exceptions import Ratelimited


def custom_exception_handler(exc, context):
    # Handle django-ratelimit's Ratelimited exception → clean 429 JSON
    if isinstance(exc, Ratelimited):
        return Response(
            {'error': 'Too many requests. Please try again later.', 'code': 'rate_limit_exceeded'},
            status=429
        )

    response = exception_handler(exc, context)

    if response is not None:
        detail = response.data
        if isinstance(detail, dict):
            first_key = next(iter(detail), None)
            if first_key:
                val = detail[first_key]
                message = val[0] if isinstance(val, list) else str(val)
            else:
                message = 'An error occurred.'
        elif isinstance(detail, list):
            message = str(detail[0]) if detail else 'An error occurred.'
        else:
            message = str(detail)

        code = getattr(getattr(exc, 'detail', exc), 'code', None) or _status_to_code(response.status_code)
        response.data = {'error': message, 'code': code}

    return response


def _status_to_code(status_code):
    mapping = {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        409: 'conflict',
        429: 'rate_limit_exceeded',
        500: 'internal_server_error',
    }
    return mapping.get(status_code, 'error')