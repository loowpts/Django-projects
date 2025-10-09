from django.db import models
from django.conf import settings
from apps.courses.models import Course
from django.utils.translation import gettext_lazy as _


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments', verbose_name=_('Студент')
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='enrollments', verbose_name=_('Курс')
    )
    enrolled_at = models.DateTimeField(_('Дата записи'), auto_now_add=True)

    class Meta:
        verbose_name = _('Запись на курс')
        verbose_name_plural = _('Записи на курс')
        ordering = ['-enrolled_at']
        constraints = [
            models.UniqueConstraint(fields=('student', 'course'), name='unique_enrollment_student'),
        ]
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['course']),
        ]

    def __str__(self):
        return f'{self.student} in {self.course}'