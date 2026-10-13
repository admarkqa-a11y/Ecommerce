from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .adapters import InvalidWebhook,InvalidProviderResponse,ProviderUnavailable
from .models import PaymentAttempt
from .card import webhook

@csrf_exempt
@require_POST
def skipcash_webhook(request):
    # Authentication is the provider signature, not a browser session.
    if len(request.body)>65536:return JsonResponse({'detail':'Payload too large'},status=413)
    try:webhook('skipcash',request.body,request.headers)
    except InvalidWebhook:return JsonResponse({'detail':'Invalid signature'},status=401)
    except PaymentAttempt.DoesNotExist:return JsonResponse({'detail':'Unknown payment'},status=404)
    except (ProviderUnavailable,InvalidProviderResponse):return JsonResponse({'detail':'Reconciliation pending'},status=503)
    return JsonResponse({'received':True})
