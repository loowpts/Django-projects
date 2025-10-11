from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from .models import Course, Category, Lesson
from .forms import CourseForm, CourseSearchForm, LessonForm
from apps.enrollments.forms import EnrollmentForm
from apps.enrollments.models import Enrollment
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
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
        self.form = CourseSearchForm(self.request.GET or None)

        if self.form.is_valid():
            query = self.form.cleaned_data.get('query')
            category = self.form.cleaned_data.get('category')

            if query:
                qs = qs.filter(
                    Q(title__icontains=query) |
                    Q(description__icontains=query)
                )
            if category:
                qs = qs.filter(category=category)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = getattr(self, 'form', CourseSearchForm())
        return ctx


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        course = self.object

        enrolled = False
        if user.is_authenticated and getattr(user, 'role', None) == 'student':
            enrolled = Enrollment.objects.filter(student=user, course=course).exists()
            if not enrolled:
                ctx['enroll_form'] = EnrollmentForm()

        ctx['enrolled'] = enrolled
        ctx['lessons'] = course.lessons.all() if enrolled else []

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
    success_url = reverse_lazy('courses:course_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def test_func(self):
        course = super().get_object()
        user = self.request.user
        return user.is_staff or course.teacher == user
    
    def handle_no_permission(self):
        messages.error(self.request, 'У вас нету доступа для редактирования.')
        return super().handle_no_permission()


class LessonCreateView(LoginRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=self.kwargs.get('course_id'))

        if request.user != self.course.teacher:
            messages.error(request, "Вы не являетесь преподавателем этого курса.")
            return redirect('courses:course_detail', pk=self.course.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.course = self.course
        response = super().form_valid(form)
        messages.success(self.request, 'Урок создан.')
        return response

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.course.pk})