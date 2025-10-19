from django.shortcuts import get_object_or_404
from django.views.generic import CreateView
from .models import Enrollment
from .forms import EnrollmentForm
from apps.courses.models import Course
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.conf import settings


class EnrollmentCreateView(LoginRequiredMixin, CreateView):
    model = Enrollment
    form_class = EnrollmentForm

    def form_valid(self, form):
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        form.instance.course = course
        form.instance.student = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Вы успешно записаны на курс.')
        return response

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk':self.object.course.pk})

    def handle_no_permission(self):
        messages.info(self.request, 'Пожалуйста, войдите в систему, чтобы записаться на курс.')
        return redirect_to_login(self.request.get_full_path(), settings.LOGIN_URL)
