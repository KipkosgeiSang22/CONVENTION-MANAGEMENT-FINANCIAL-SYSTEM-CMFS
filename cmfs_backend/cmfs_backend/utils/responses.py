from rest_framework.response import Response
from rest_framework import status as http_status


def success(data=None, message='ok', status=http_status.HTTP_200_OK):
    payload = {'status': 'ok', 'message': message}
    if data is not None:
        payload['data'] = data
    return Response(payload, status=status)


def created(data=None, message='created'):
    return success(data=data, message=message, status=http_status.HTTP_201_CREATED)


def error(message, code='error', status=http_status.HTTP_400_BAD_REQUEST):
    return Response({'error': message, 'code': code}, status=status)