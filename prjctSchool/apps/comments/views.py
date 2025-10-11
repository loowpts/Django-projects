from django.shortcuts import redirect, get_object_or_404
from django.views.generic import CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse
from django.contrib import messages
from .models import Comment
from .forms import CommentForm
from apps.courses.models import Lesson, Course
from apps.enrollments.models import Enrollment

class CommentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'comments/comment_form.html'

    def test_func(self):
        lesson = get_object_or_404(Lesson, pk=self.kwargs['lesson_id'])
        return (self.request.user.role == 'student' and
                Enrollment.objects.filter(student=self.request.user, course=lesson.course).exists())

    def form_valid(self, form):
        lesson = get_object_or_404(Lesson, pk=self.kwargs['lesson_id'])
        form.instance.lesson = lesson
        form.instance.user = self.request.user
        parent_id = self.request.POST.get('parent_id')
        if parent_id:
            form.instance.parent = get_object_or_404(Comment, pk=parent_id)
        response = super().form_valid(form)
        messages.success(self.request, 'Комментарий добавлен.')
        return response

    def get_success_url(self):
        lesson = get_object_or_404(Lesson, pk=self.kwargs['lesson_id'])
        return reverse('courses:course_detail', kwargs={'pk': lesson.course.pk})

    def handle_no_permission(self):
        messages.error(self.request, 'Комментарии могут добавлять только зачисленные студенты.')
        lesson = get_object_or_404(Lesson, pk=self.kwargs['lesson_id'])
        return redirect('courses:course_detail', pk=lesson.course.pk)

class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = 'comments/comment_confirm_delete.html'

    def test_func(self):
        comment = self.get_object()
        return comment.user == self.request.user

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.lesson.course.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Комментарий удалён.')
        return super().form_valid(form)

    def handle_no_permission(self):
        messages.error(self.request, 'Вы можете удалять только свои комментарии.')
        return redirect('courses:course_detail', pk=self.object.lesson.course.pk)