from django.db.models.query import QuerySet
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView, CreateView, FormView, DeleteView
from .models import Course, Category, Lesson
from .forms import CourseForm
from django.db.models import Q, F
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.urls import reverse, reverse_lazy
from django.template.response import TemplateResponse
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib import messages
from taggit.models import Tag
from django.utils import timezone
from django.core.exceptions import PermissionDenied


# class RequestFormMixin:
#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['request'] = self.request
#         return kwargs


class CourseCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse('courses:course_list')

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
