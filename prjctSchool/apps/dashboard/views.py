from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from apps.courses.models import Course, Lesson
from apps.enrollments.models import Enrollment
from .models import LessonProgress
from apps.comments.models import Comment


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        if user.role == 'teacher':
            ctx['courses'] = Course.objects.filter(teacher=user).annotate(student_count=Count('enrollments'))
            ctx['total_students'] = sum(course.student_count for course in ctx['courses'])
        elif user.role == 'student':
            enrollments = Enrollment.objects.filter(student=user).select_related('course')
            ctx['enrolled_courses'] = []
            for enrollment in enrollments:
                course = enrollment.course
                lessons = Lesson.objects.filter(course=course)
                completed_lessons = LessonProgress.objects.filter(
                    student=user,
                    lesson__course=course,
                    completed=True
                ).count()
                total_lessons = lessons.count()
                progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
                ctx['enrolled_courses'].append({
                    'course': course,
                    'progress': round(progress, 1),
                    'completed_lessons': completed_lessons,
                    'total_lessons': total_lessons,
                })
            ctx['recent_comments'] = Comment.objects.filter(user=user).order_by('-created_at')[:5]
            ctx['total_courses'] = len(ctx['enrolled_courses'])

        ctx['role'] = user.role
        return ctx