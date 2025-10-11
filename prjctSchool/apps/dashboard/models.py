from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.courses.models import Lesson
from django.conf import settings

class LessonProgress(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_progresses',
        verbose_name=_('Студент')
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='progresses',
        verbose_name=_('Урок')
    )
    completed = models.BooleanField(_('Завершено'), default=False)
    completed_at = models.DateTimeField(_('Дата завершения'), null=True, blank=True)

    class Meta:
        verbose_name = _('Прогресс урока')
        verbose_name_plural = _('Прогресс уроков')
        unique_together = ('student', 'lesson')

    def __str__(self):
        return f'{self.student.username} - {self.lesson.title} ({"Завершено" if self.completed else "Не завершено"})'