"""OpenAPI for implemented actions; dynamic JSON fields are explicitly open-ended."""
import re
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema, OpenApiTypes, inline_serializer
from rest_framework import serializers


class RetailSchema(AutoSchema):
    def get_operation_id(self):
        return re.sub(r'[^a-zA-Z0-9_]+','_',self.path.strip('/'))+'_'+self.method.lower()


def implemented_methods(endpoints):
    result=[]
    for path,regex,method,callback in endpoints:
        if path=='/api/v1/admin/variants' and method=='POST':continue
        if path.startswith('/api/v1/admin/orders'):
            if method=='GET' and '{command}' in path:continue
            if method=='POST' and '{command}' not in path:continue
        if path.startswith('/api/v1/admin/imports/') and method=='POST' and '{command}' not in path:continue
        if path.startswith('/api/v1/admin/notifications') and method!=('POST' if '{' in path else 'GET'):continue
        if path.startswith('/api/v1/account/addresses') and method not in (['GET','PATCH','DELETE'] if '{' in path else ['GET','POST']):continue
        result.append((path,regex,method,callback))
    return result


def document_actions(api,auth):
    # These action responses contain published snapshots and configurable attributes.
    # Resource endpoints retain their generated, model-specific typed schemas.
    for module in (api,auth):
        for name,view in list(vars(module).items()):
            if not hasattr(view,'cls') or getattr(view,'__module__','')!=module.__name__:continue
            schema=extend_schema(
                request=OpenApiTypes.OBJECT,
                responses={200:OpenApiTypes.ANY,400:OpenApiTypes.OBJECT,403:OpenApiTypes.OBJECT,409:OpenApiTypes.OBJECT},
                description='Session-cookie authentication; unsafe methods require X-CSRFToken. '
                    'JSON responses may contain dynamic attribute values. See docs/backend/API.md '
                    'for command permissions and request examples.',
            )
            setattr(module,name,schema(view))
    api.quote=extend_schema(request=inline_serializer('CheckoutQuoteRequest',fields={
        'method_id':serializers.UUIDField(),'area_id':serializers.UUIDField(required=False,allow_null=True),
    }))(api.quote)
    api.place=extend_schema(request=inline_serializer('PlaceOrderRequest',fields={
        'quote_id':serializers.UUIDField(),'payment_method':serializers.ChoiceField(choices=['cod','bank','card']),
        'contact':serializers.DictField(),'address':serializers.DictField(required=False),
    }),responses={201:OpenApiTypes.OBJECT,400:OpenApiTypes.OBJECT,403:OpenApiTypes.OBJECT,409:OpenApiTypes.OBJECT})(api.place)
    auth.signin=extend_schema(request=inline_serializer('SignInRequest',fields={
        'email':serializers.EmailField(),'password':serializers.CharField(),
        'admin':serializers.BooleanField(required=False),'otp':serializers.CharField(required=False),
    }))(auth.signin)
    api.invoice=extend_schema(responses={(200,'text/html'):OpenApiTypes.STR})(api.invoice)
