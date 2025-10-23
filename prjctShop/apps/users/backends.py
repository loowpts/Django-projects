from django.contrib.auth.backends import ModelBackend
from django.conf import settings

User = settings.AUTH_USER_MODEL()


class EmailBackend(ModelBackend):
    """
    Аутентификация по email вместо username
    """
    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None:
            email = kwargs.get('email')
        if email is None or password is None:
            return
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Запускаем стандартный хешер пароля для предотвращения атак по времени
            User().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
