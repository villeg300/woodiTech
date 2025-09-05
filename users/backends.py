from django.contrib.auth.backends import ModelBackend
from .models import User

class PhoneOrEmailBackend(ModelBackend):
    def authenticate(self, request, phone=None, email=None, password=None, **kwargs):
        user = None
        identifier = phone or email or kwargs.get('username')
        if identifier:
            try:
                if '@' in identifier:
                    user = User.objects.get(email=identifier)
                else:
                    user = User.objects.get(phone=identifier)
            except User.DoesNotExist:
                return None
            if user and user.check_password(password):
                return user
        return None
