from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse
from django.db.models import Avg


class Category(models.Model):
    name = models.CharField(_('Название'), max_length=100, unique=True)
    slug = models.SlugField(_('Слаг'), max_length=100, unique=True)
    description = models.TextField(_('Описание'), blank=True, null=True)

    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(_('Тег'), max_length=50, unique=True)
    slug = models.SlugField(_('Слаг'), max_length=50, unique=True)

    class Meta:
        verbose_name = _("Тег")
        verbose_name_plural = _("Теги")
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('DRAFT')
        PUBLISHED = 'PUBLISHED', _('Published')
        CANCELLED = 'CANCELLED', _('Cancelled')

    title = models.CharField(_("Заголовок"), max_length=100)
    slug = models.SlugField(_('Слаг'), max_length=100, unique=True)
    description = models.TextField(_('Описание'))
    short_description = models.TextField(_('Краткое описание'))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name=_('Автор')
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='events',
        verbose_name=_('Категория'),
        null=True,
        blank=True
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='events',
        verbose_name=_('Теги'),
        blank=True
    )
    image = models.ImageField(_('Изображение'), upload_to='events/images/', null=True, blank=True)
    start_datetime = models.DateTimeField(_('Дата и время начала'), default=timezone.now)
    end_datetime = models.DateTimeField(_('Дата и время окончания'), null=True, blank=True)
    location = models.CharField(_('Местоположение'), max_length=255, null=True, blank=True)
    status = models.CharField(_('Статус'), max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(_('Просмотры'), default=0)

    class Meta:
        verbose_name = _('Событие')
        verbose_name_plural = _('События')
        ordering = ['-start_datetime']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('events:event_detail', kwargs={'slug': self.slug})

    def average_rating(self):
        try:
            agg = self.reviews.filter(approved=True).aggregate(avg=Avg('rating'))
            return round(agg['avg'], 1) if agg['avg'] else None
        except Exception:
            return None

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)


class Review(models.Model):
    class Rating(models.IntegerChoices):
        ONE = 1, _('1')
        TWO = 2, _('2')
        THREE = 3, _('3')
        FOUR = 4, _('4')
        FIVE = 5, _('5')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Пользователь')
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Событие')
    )
    rating = models.PositiveSmallIntegerField(_('Рейтинг'), choices=Rating.choices, default=Rating.FIVE)
    text = models.TextField(_('Текст отзыва'), blank=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    approved = models.BooleanField(_('Одобрен'), default=False)

    class Meta:
        verbose_name = _('Отзыв')
        verbose_name_plural = _('Отзывы')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'event'], name='unique_rating'),
        ]

    def __str__(self):
        return f'{self.user} - {self.event} ({self.rating})'