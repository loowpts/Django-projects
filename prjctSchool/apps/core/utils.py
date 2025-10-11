from django.utils.text import slugify
from apps.dashboard.models import LessonProgress
from apps.courses.models import Lesson

def calculate_course_progress(user, course):
    lessons = Lesson.objects.filter(course=course)
    total_lessons = lessons.count()
    if total_lessons == 0:
        return 0
    completed_lessons = LessonProgress.objects.filter(
        student=user, lesson__course=course, completed=True
    ).count()
    return round((completed_lessons / total_lessons) * 100, 1)

def generate_slug(title, model_class, instance=None):
    base_slug = slugify(title, allow_unicode=True)
    slug = base_slug
    num = 1
    while model_class.objects.filter(slug=slug).exclude(id=instance.id if instance else None).exists():
        slug = f"{base_slug}-{num}"
        num += 1
    return slug