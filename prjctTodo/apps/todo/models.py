from django.db import models
from apps.users.models import User


class Task(models.Model):
    class Priority(models.IntegerChoices):
        """Уровни приоритета задачи."""
        LOW = 1, "Низкий"
        MED = 2, "Средний"
        HIGH = 3, "Высокий"

    class Status(models.TextChoices):
        """Статусы выполнения задачи."""
        TODO = 'todo', 'К выполнению'
        IN_PROGRESS = 'in_progress', 'В работе'
        DONE = 'done', 'Готово'
        ARCHIVED = 'archived', 'Архив'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200, verbose_name='Название')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TODO, db_index=True)
    priority = models.IntegerField(choices=Priority.choices, default=Priority.LOW)
    description = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    is_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Keep is_done in sync with status
        if self.status == self.Status.DONE:
            self.is_done = True
        elif self.status in {self.Status.TODO, self.Status.IN_PROGRESS}:
            self.is_done = False

        # Archived tasks must have ARCHIVED status
        if self.is_archived:
            self.status = self.Status.ARCHIVED

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    