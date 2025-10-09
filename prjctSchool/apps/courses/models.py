from django.db import models
from apps.users.models import User
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(_('Название'), max_length=100)
    slug = models.SlugField(_('Слаг'), max_length=100, unique=True)

    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Course(models.Model):
    title = models.CharField(_('Заголовок'), max_length=100)
    description = models.TextField(_('Описание'))
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='courses', verbose_name=_('Категория')
        )
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='courses', verbose_name=_('Учитель')
        )
    main_image = models.ImageField(_('Обложка'), upload_to='course/')
    created_at = models.DateTimeField(_('Дата регистрации'), auto_now_add=True)

    class Meta:
        verbose_name = _('Курс')
        verbose_name_plural = _('Курсы')
        ordering = ['-created_at']
    
    def is_teacher(self, user):
        return self.teacher == user

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='lessons',  verbose_name=_('Курс')
        )
    title = models.CharField(_('Заголовок'), max_length=100)
    content = models.TextField(_('Контент'))
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('Урок')
        verbose_name_plural = _('Уроки')
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(fields=['course', 'order'], name='unique_course_order'),
        ]

    def __str__(self):
        return f'{self.title} - ({self.course.title}).'
