from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from apps.courses.models import Course, Lesson
from apps.enrollments.models import Enrollment
from apps.dashboard.models import LessonProgress
from apps.comments.models import Comment
from apps.core.utils import calculate_course_progress
from apps.core.mixins import RoleRequiredMixin

class DashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'
    allowed_roles = ['teacher', 'student']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_teacher:
            ctx['courses'] = Course.objects.filter(teacher=user).annotate(student_count=Count('enrollments'))
            ctx['total_students'] = sum(course.student_count for course in ctx['courses'])
        elif user.is_student:
            enrollments = Enrollment.objects.filter(student=user).select_related('course')
            ctx['enrolled_courses'] = []
            for enrollment in enrollments:
                course = enrollment.course
                progress = calculate_course_progress(user, course)
                lessons = Lesson.objects.filter(course=course)
                completed_lessons = LessonProgress.objects.filter(student=user, lesson__course=course, completed=True).count()
                total_lessons = lessons.count()
                ctx['enrolled_courses'].append({
                    'course': course,
                    'progress': progress,
                    'completed_lessons': completed_lessons,
                    'total_lessons': total_lessons,
                })
            ctx['recent_comments'] = Comment.objects.filter(user=user).order_by('-created_at')[:5]
            ctx['total_courses'] = len(ctx['enrolled_courses'])

        ctx['role'] = user.role
        return ctx