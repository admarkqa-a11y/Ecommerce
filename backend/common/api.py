from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_handler
from rest_framework.response import Response

class Conflict(APIException):
    status_code = 409
    default_detail = 'The data changed. Refresh and try again.'
    default_code = 'conflict'

def exception_handler(exc, context):
    from apps.payments.adapters import ProviderUnavailable,InvalidProviderResponse
    if isinstance(exc,(ProviderUnavailable,InvalidProviderResponse)):
        return Response({'code':'payment_reconciliation_required','detail':str(exc)},status=503)
    if isinstance(exc, DjangoValidationError):
        return Response({'code': 'validation_error', 'detail': getattr(exc, 'message_dict', exc.messages)}, status=400)
    if isinstance(exc, IntegrityError):
        return Response({'code': 'conflict', 'detail': 'A conflicting record or invalid relationship exists.'}, status=409)
    return drf_handler(exc, context)
