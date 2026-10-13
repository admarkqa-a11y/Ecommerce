from rest_framework.permissions import BasePermission

class StaffCapability(BasePermission):
    def has_permission(self, request, view):
        required = getattr(view, 'capability', '')
        if isinstance(required, dict):
            required = required.get(getattr(view, 'action', ''), required.get(request.method, ''))
        return bool(required and request.user.is_authenticated and request.user.can(required)
                    and request.session.get('staff_mfa'))

