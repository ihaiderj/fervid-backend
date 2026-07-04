from rest_framework import status
from rest_framework.response import Response


def success_response(data=None, message=None, status_code=status.HTTP_200_OK):
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    if message:
        payload["message"] = message
    return Response(payload, status=status_code)


def error_response(error, code=None, status_code=status.HTTP_400_BAD_REQUEST):
    payload = {"success": False, "error": error}
    if code:
        payload["code"] = code
    return Response(payload, status=status_code)
