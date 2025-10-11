from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Enrollment
from apps.dashboard.models import LessonProgress
from apps.courses.models import Lesson

@receiver(post_save, sender=Enrollment)
def create_lesson_progress(sender, instance, created, **kwargs):
    if created:
        lessons = Lesson.objects.filter(course=instance.course)
        for lesson in lessons:
            LessonProgress.objects.get_or_create(
                student=instance.student,
                lesson=lesson,
                defaults={'completed': False}
            )