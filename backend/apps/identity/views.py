import base64,hashlib,json,secrets,time
from datetime import timedelta
import pyotp
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.crypto import constant_time_compare,salted_hmac
from rest_framework.decorators import api_view,permission_classes,throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.throttling import ScopedRateThrottle,AnonRateThrottle
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError,AuthenticationFailed
from .models import User,EmailChallenge

class AuthThrottle(AnonRateThrottle):
    scope='auth'
    def get_cache_key(self,request,view):
        return self.cache_format % {'scope':self.scope,'ident':self.get_ident(request)}

def mark_login(request):
    request.session['authenticated_at']=time.time()
    request.session['last_activity']=time.time()

def cipher():
    key=settings.FIELD_ENCRYPTION_KEY or base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest()).decode()
    return Fernet(key.encode())

def user_data(user,session):
    return {'id':str(user.id),'email':user.email,'name':user.first_name,'locale':user.locale,
            'staff':user.is_staff,'staff_mfa':bool(session.get('staff_mfa')),
            'capabilities':['*'] if user.is_superuser else sorted({c for r in user.roles.all() for c in r.capabilities})}

@api_view(['GET'])
@permission_classes([AllowAny])
def csrf(request):return Response({'csrfToken':get_token(request)})

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def register(request):
    SessionAuthentication().enforce_csrf(request)
    email=str(request.data.get('email','')).strip().lower();validate_email(email)
    password=request.data.get('password','');validate_password(password)
    if User.objects.filter(email=email).exists():raise ValidationError('Unable to register with these details. Try signing in or recovery.')
    user=User.objects.create_user(username=email,email=email,password=password,first_name=str(request.data.get('name',''))[:150])
    login(request,user);request.session.pop('staff_mfa',None)
    mark_login(request)
    return Response(user_data(user,request.session),status=201)

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def signin(request):
    SessionAuthentication().enforce_csrf(request)
    email=str(request.data.get('email','')).strip().lower()
    user=authenticate(request,username=email,password=request.data.get('password',''))
    if not user:raise AuthenticationFailed('Invalid credentials.')
    if request.data.get('admin'):
        if not user.is_staff or not user.mfa_secret:raise AuthenticationFailed('Staff access requires configured MFA.')
        with transaction.atomic():
            user=User.objects.select_for_update().get(pk=user.pk)
            totp=pyotp.TOTP(cipher().decrypt(user.mfa_secret.encode()).decode())
            counter=totp.timecode(timezone.now())
            if counter<=user.mfa_last_counter or not totp.verify(str(request.data.get('otp','')),valid_window=0):
                raise AuthenticationFailed('Invalid or already used MFA code.')
            user.mfa_last_counter=counter;user.save(update_fields=['mfa_last_counter'])
        login(request,user);request.session['staff_mfa']=True;request.session.set_expiry(1800)
    else:
        login(request,user);request.session.pop('staff_mfa',None)
    mark_login(request)
    return Response(user_data(user,request.session))

@api_view(['GET','PATCH'])
def session(request):
    if request.method=='PATCH':
        request.user.first_name=str(request.data.get('name',request.user.first_name))[:150]
        locale=request.data.get('locale',request.user.locale)
        if locale not in ['en','ar']:raise ValidationError('Unsupported locale.')
        request.user.locale=locale;request.user.save()
    return Response(user_data(request.user,request.session))

@api_view(['POST'])
def signout(request):logout(request);return Response({'ok':True})

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def request_otp(request):
    SessionAuthentication().enforce_csrf(request)
    email=str(request.data.get('email','')).strip().lower();validate_email(email)
    if EmailChallenge.objects.filter(email=email,created_at__gt=timezone.now()-timedelta(seconds=60)).exists():
        return Response({'detail':'If eligible, a code has been sent.'})
    code=f'{secrets.randbelow(1000000):06d}'
    EmailChallenge.objects.filter(email=email,consumed=False).update(consumed=True)
    EmailChallenge.objects.create(email=email,digest=salted_hmac('email-otp',email+code).hexdigest(),expires_at=timezone.now()+timedelta(minutes=10))
    send_mail('Your sign-in code',f'Your code is {code}. It expires in 10 minutes.',settings.DEFAULT_FROM_EMAIL,[email])
    return Response({'detail':'If eligible, a code has been sent.'})

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def verify_otp(request):
    SessionAuthentication().enforce_csrf(request)
    email=str(request.data.get('email','')).strip().lower()
    valid=False
    with transaction.atomic():
        challenge=EmailChallenge.objects.select_for_update().filter(email=email,consumed=False,expires_at__gt=timezone.now(),attempts__lt=5).order_by('-created_at').first()
        if challenge:
            challenge.attempts+=1
            valid=constant_time_compare(challenge.digest,salted_hmac('email-otp',email+str(request.data.get('code',''))).hexdigest())
            challenge.consumed=valid;challenge.save()
    if not valid:raise AuthenticationFailed('Invalid or expired code.')
    user=User.objects.filter(email=email).first()
    if not user:
        user=User(username=email,email=email);user.set_unusable_password();user.save()
    if not user.is_active:raise AuthenticationFailed('Unable to sign in.')
    user.email_verified=True;user.save()
    login(request,user,backend='django.contrib.auth.backends.ModelBackend');request.session.pop('staff_mfa',None)
    mark_login(request)
    return Response(user_data(user,request.session))

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def password_reset_request(request):
    SessionAuthentication().enforce_csrf(request)
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    email=str(request.data.get('email','')).strip().lower();validate_email(email)
    user=User.objects.filter(email=email,is_active=True,is_staff=False).first()
    if user and settings.CUSTOMER_ORIGIN:
        uid=urlsafe_base64_encode(force_bytes(str(user.pk)))
        token=default_token_generator.make_token(user)
        url=f'{settings.CUSTOMER_ORIGIN}/reset-password?uid={uid}&token={token}'
        send_mail('Reset your password',f'Open this link to reset your password. It expires in 15 minutes.\n{url}',settings.DEFAULT_FROM_EMAIL,[email])
    return Response({'detail':'If eligible, a password reset link has been sent.'})

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def password_reset_confirm(request):
    SessionAuthentication().enforce_csrf(request)
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from uuid import UUID
    try:uid=UUID(urlsafe_base64_decode(str(request.data.get('uid',''))).decode())
    except (ValueError,UnicodeError,TypeError):raise ValidationError('Invalid or expired reset link.')
    with transaction.atomic():
        user=User.objects.select_for_update().filter(pk=uid,is_active=True,is_staff=False).first()
        if not user or not default_token_generator.check_token(user,str(request.data.get('token',''))):raise ValidationError('Invalid or expired reset link.')
        password=request.data.get('password','');validate_password(password,user)
        user.set_password(password);user.save(update_fields=['password'])
    return Response({'changed':True})

@api_view(['POST'])
@throttle_classes([AuthThrottle])
def password_change(request):
    from django.contrib.auth import update_session_auth_hash
    if not request.user.check_password(request.data.get('current_password','')):raise AuthenticationFailed('Current password required.')
    password=request.data.get('password','');validate_password(password,request.user)
    request.user.set_password(password);request.user.save(update_fields=['password'])
    update_session_auth_hash(request,request.user)
    return Response({'changed':True})
