from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.models import EmailAddress
from django.utils.translation import gettext_lazy as _
from allauth.account.utils import user_email


class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        data = form.cleaned_data
        user.email = data.get('email', '').lower()
        user.first_name = data.get('first_name', '')
        user.last_name = data.get('last_name', '')
        user.is_verified = False
        if commit:
            user.save()
        return user

    def populate_username(self, request, user):
        user.username = user.email
        return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        # Безопасное чтение email (может быть None)
        email = data.get("email") or sociallogin.account.extra_data.get("email") or ""
        if email:
            # нормализуем email через функцию allauth
            email = user_email(user, email) or email
            user.email = email
        else:
            # Если email не пришёл — оставляем пустым; можно потребовать ввод позже
            user.email = user.email or ""

        # Обработка имени/фамилии — провайдеры дают по-разному
        first_name = data.get("first_name") or data.get("given_name") or ""
        last_name = data.get("last_name") or data.get("family_name") or ""
        # Если есть одно поле 'name', разбиваем на части
        if not first_name and not last_name:
            full = data.get("name") or data.get("fullname") or sociallogin.account.extra_data.get("name") or ""
            if full:
                parts = full.split()
                first_name = parts[0]
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Сохраняем в user, только если есть значение (чтобы не перезаписать существующие)
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name

        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Сохранение пользователя и пометка email как verified если провайдер подтвердил.
        """
        user = sociallogin.user
        # Вызов оригинальной логики (создание/сохранение пользователя)
        user = super().save_user(request, sociallogin, form)

        # Попытка пометить email как verified в EmailAddress
        # Провайдеры обычно дают флаг: 'email_verified' или 'verified_email' или т.п.
        extra = sociallogin.account.extra_data or {}
        email_verified = (
            extra.get("email_verified")
            or extra.get("verified")
            or extra.get("verified_email")
            or extra.get("emailVerified")
        )

        # Если наш user имеет email — создаём/обновляем EmailAddress
        if user.email:
            EmailAddress.objects.update_or_create(
                user=user,
                email=user.email,
                defaults={"verified": bool(email_verified), "primary": True},
            )

        return user
