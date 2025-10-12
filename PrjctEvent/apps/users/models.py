from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator
from django.conf import settings


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('E-mail must be set')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        _('email'),
        unique=True,
        db_index=True,
        validators=[EmailValidator()],
    )
    first_name = models.CharField(_('Имя'), max_length=150, blank=True)
    last_name = models.CharField(_('фамилия'), max_length=150, blank=True)

    # Служебные флаги
    is_active = models.BooleanField(_('активен'), default=True)
    is_staff = models.BooleanField(_('персонал'), default=False)
    is_verified = models.BooleanField(_('e-mail подтверждён'), default=False)

    # Метаданные
    date_joined = models.DateTimeField(_('дата регистрации'), default=timezone.now)
    updated_at = models.DateTimeField(_('обновлён'), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = _('пользователь')
        verbose_name_plural = _('пользователи')

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return (f'{self.first_name} {self.last_name}').strip()


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ORGANIZER = 'organizer', _('Организатор')
        PARTICIPANT = 'participant', _('Участник')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        models.CASCADE,
        related_name='profile',
    )
    avatar = models.ImageField(_('аватар'), upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(_('о себе'), blank=True)
    role = models.CharField(_('роль'), max_length=20, choices=Role.choices, default=Role.PARTICIPANT)
    is_public = models.BooleanField(_('профиль публичный'), default=True)
    timezone = models.CharField(_('часовой пояс'), max_length=50, blank=True)
    streak_visibility = models.BooleanField(_('показывать прогресс/стрик'), default=True)

    class Meta:
        verbose_name = _('профиль пользователя')
        verbose_name_plural = _('профили пользователей')

    def __str__(self):
        return f'Профиль: {self.user}'
