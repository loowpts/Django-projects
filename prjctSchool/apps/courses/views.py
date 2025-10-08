from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from .models import Course, Category, Lesson
from .forms import CourseForm
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.exceptions import PermissionDenied


# class RequestFormMixin:
#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['request'] = self.request
#         return kwargs

class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 10

    def get_queryset(self):
        qs = Course.objects.select_related('teacher', 'category').all()
        q = (self.request.GET.get('q') or '').strip()
        category = (self.request.GET.get('category') or '')

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if category and category.isdigit():
            qs = qs.filter(category_id=int(category))
        return  qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = (self.request.GET.get('q') or '').strip()
        ctx['category'] = (self.request.GET.get('category') or '').strip()
        return ctx


class CourseDetailView(DetailView):
    """
        Потом реализовать
        enroll_form=EnrollmentForm()
        if user.is_student and not enrolled.
    """
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx


class CourseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('courses:course_list')

    def test_func(self):
        course = self.get_object()
        user = self.request.user
        return user.is_staff or course.teacher == user

    def handle_no_permission(self):
        raise PermissionDenied('Вы не можете удалить данный курс.')


class CourseCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:course_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def test_func(self):
        return getattr(self.request.user, 'role', None) == 'teacher'
    
    def handle_no_permission(self):
        messages.error(self.request, 'Доступ разрешён только учителям.')
        return super().handle_no_permission()


class CourseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def test_func(self):
        course = super().get_object()
        return course.is_teacher(self.request.user)
    
    def handle_no_permission(self):
        messages.error(self.request, 'У вас нету доступа для редактирования.')
        return super().handle_no_permission()
