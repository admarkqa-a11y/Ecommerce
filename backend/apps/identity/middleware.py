import time
from django.contrib.auth import logout

class SessionLifetimeMiddleware:
    """Idle and absolute expiry; host-only cookies remain the default."""
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.user.is_authenticated:
            now=time.time();staff=bool(request.session.get('staff_mfa'))
            idle=1800 if staff else 14*86400;absolute=12*3600 if staff else 30*86400
            started=request.session.get('authenticated_at',now)
            previous=request.session.get('last_activity',now)
            if now-started>=absolute or now-previous>=idle:logout(request)
            else:
                request.session['authenticated_at']=started;request.session['last_activity']=now
                request.session.set_expiry(max(1,min(idle,int(absolute-(now-started)))))
        return self.get_response(request)
