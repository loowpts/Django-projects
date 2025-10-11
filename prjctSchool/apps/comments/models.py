from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.courses.models import Lesson
from django.conf import settings


class Comment(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Урок')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Пользователь')
    )
    text = models.TextField(_('Текст комментария'))
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name=_('Родительский комментарий')
    )

    class Meta:
        verbose_name = _('Комментарий')
        verbose_name_plural = _('Комментарии')
        ordering = ['-created_at']

    def __str__(self):
        return f'Комментарий от {self.user.username} к уроку {self.lesson.title}'