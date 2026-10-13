"""SkipCash hosted checkout adapter, based on official integration manual v1.4.

Merchant sandbox verification against the current provider contract is a launch gate.
No card data enters this backend. Refund execution remains a verified merchant-portal
operation because a current official refund API contract has not been supplied.
"""
import base64
import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation
from uuid import UUID
from urllib.parse import urlparse
import requests
from django.conf import settings
from .adapters import PaymentResult, ProviderUnavailable, InvalidProviderResponse, InvalidWebhook

CREATE_FIELDS=('Uid','KeyId','Amount','FirstName','LastName','Phone','Email','Street','City','State','Country','PostalCode','TransactionId','Custom1')
WEBHOOK_FIELDS=('PaymentId','Amount','StatusId','TransactionId','Custom1','VisaId')

def signature(data,fields,secret):
    values={key.lower():value for key,value in data.items()}
    canonical=','.join(f'{key}={values[key.lower()]}' for key in fields if values.get(key.lower()) not in (None,''))
    return base64.b64encode(hmac.new(secret.encode(),canonical.encode(),hashlib.sha256).digest()).decode()

class SkipCashAdapter:
    currencies=('QAR',)  # Provider contract limitation; store currency remains configurable.
    supports_refund_api=False

    def ready(self):
        return all([settings.SKIPCASH_CLIENT_ID,settings.SKIPCASH_KEY_ID,settings.SKIPCASH_KEY_SECRET,settings.SKIPCASH_WEBHOOK_KEY])

    def _request(self,method,path,body=None):
        if not self.ready():raise ProviderUnavailable('SkipCash credentials are not configured.')
        origin='https://api.skipcash.app' if settings.SKIPCASH_ENV=='production' else 'https://skipcashtest.azurewebsites.net'
        authorization=signature(body,CREATE_FIELDS,settings.SKIPCASH_KEY_SECRET) if body is not None else settings.SKIPCASH_CLIENT_ID
        try:
            response=requests.request(method,origin+path,json=body,headers={'Authorization':authorization,'Accept':'application/json'},
                timeout=(5,20),allow_redirects=False)
            response.raise_for_status()
            if response.status_code!=200:raise ProviderUnavailable('Unexpected gateway status.')
            data=json.loads(response.content,parse_float=Decimal)
            if data.get('hasError') or data.get('hasValidationError'):raise ProviderUnavailable('Gateway rejected the request; reconcile before retry.')
            return self._result(data['resultObj'])
        except (requests.RequestException,ValueError,KeyError,TypeError,InvalidOperation):
            raise ProviderUnavailable('Gateway outcome could not be verified.') from None

    def _result(self,data):
        try:
            reference=str(UUID(data['id']))
            amount=Decimal(str(data['amount']));currency=data['currency']
            if not amount.is_finite() or amount<0 or currency not in self.currencies:raise ValueError()
            status={0:'pending',1:'pending',2:'paid',3:'failed',4:'failed',5:'failed',6:'external_refund',7:'external_refund',8:'external_refund'}.get(data['statusId'],'unknown')
            url=data.get('payUrl') or None
            if url:
                parsed=urlparse(url)
                if parsed.scheme!='https' or parsed.hostname not in settings.SKIPCASH_CHECKOUT_HOSTS or parsed.username or parsed.password:
                    raise ValueError()
            return PaymentResult(reference,status,amount,currency,url,str(data.get('transactionId') or ''))
        except (KeyError,ValueError,TypeError,InvalidOperation):raise InvalidProviderResponse('Invalid SkipCash response.') from None

    def create_payment(self,request):
        if request.currency not in self.currencies:raise InvalidProviderResponse('Unsupported SkipCash merchant currency.')
        first,_,last=request.contact.get('name','').strip().partition(' ')
        body={'uid':request.attempt_id,'keyId':settings.SKIPCASH_KEY_ID,'amount':f'{request.amount:.2f}',
            'firstName':first[:50],'lastName':(last or first)[:50],'phone':request.contact.get('phone',''),
            'email':request.contact.get('email',''),'transactionId':request.attempt_id}
        return self._request('POST','/api/v1/payments',body)

    def retrieve_payment(self,reference):
        try:reference=str(UUID(reference))
        except (ValueError,TypeError,AttributeError):raise InvalidProviderResponse('Payment reference must be a UUID.') from None
        return self._request('GET','/api/v1/payments/'+reference)

    def verify_and_parse_webhook(self,body,headers):
        if not settings.SKIPCASH_WEBHOOK_KEY:raise InvalidWebhook('Webhook is not configured.')
        try:
            data=json.loads(body,parse_float=Decimal)
            if not isinstance(data,dict):raise ValueError()
            expected=signature(data,WEBHOOK_FIELDS,settings.SKIPCASH_WEBHOOK_KEY)
            supplied=headers.get('Authorization','')
            if not hmac.compare_digest(expected,supplied):raise ValueError()
            data={key.lower():value for key,value in data.items()}
            reference=str(UUID(data['paymentid']));attempt=str(UUID(data['transactionid']))
        except (ValueError,KeyError,TypeError):raise InvalidWebhook('Invalid webhook signature or identifiers.') from None
        # The signed message is a notification only. Retrieve authoritative state.
        return reference,attempt

    def request_refund(self,*args,**kwargs):
        raise ProviderUnavailable('Record a verified merchant-portal refund; automated SkipCash refund contract is not configured.')

    def retrieve_refund(self,*args,**kwargs):
        raise ProviderUnavailable('Refund reconciliation requires the verified merchant-portal reference.')
