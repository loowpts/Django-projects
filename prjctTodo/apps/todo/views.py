from django.db.models.query import QuerySet
from django.db.models import Q
from django.http.response import HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Task
from .forms import TaskForm
from django.utils import timezone
from django.views.generic import ListView, DetailView, DeleteView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.exceptions import PermissionDenied


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'todo/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 10

    def get_queryset(self):
        qs = Task.objects.filter(user=self.request.user)
        q = (self.request.GET.get('q') or '').strip()
        status = (self.request.GET.get('status') or '')
        priority = (self.request.GET.get('priority') or '')

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx['params'] = {
            'q': (self.request.GET.get('q') or '').strip(),
            'status': (self.request.GET.get('status') or '').strip(),
            'priority': (self.request.GET.get('priority') or '').strip(),
        }
        return ctx


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'todo/task_detail.html'
    context_object_name = 'task'

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        task = self.object
        today = timezone.localdate()

        ctx['today'] = today
        ctx['is_today_created'] = (task.created_at.date() == today)
        ctx['status_display'] = (task.get_status_display())
        ctx['priority_display'] = (task.get_priority_display())

        ctx['related_tasks'] = (
            Task.objects.filter(user=self.request.user)
            .exclude(id=task.id)
            .filter(status=task.status)
            [:5]
        )
        return ctx


class TaskCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'todo/task_form.html'
    success_url = reverse_lazy('todo:task_list')
    success_message = 'Задача создана'

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class TaskUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'todo/task_form.html'
    success_url = reverse_lazy('todo:task_list')
    success_message = 'Задача успешно создана'

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class TaskDeleteView(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, DeleteView):
    model = Task
    template_name = 'todo/task_confirm_delete.html'
    success_url = reverse_lazy('todo:task_list')
    success_message = 'Задача удалена.'

    def test_func(self):
        obj = self.get_object()
        return obj.user_id == self.request.user.id

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        return response

    def handle_no_permission(self) -> HttpResponseRedirect:
        raise PermissionDenied("Вы не можете удалить эту задачу")


class ToggleTaskDoneView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, user=request.user)
        task.is_done = not task.is_done
        if task.is_done:
            task.status = Task.Status.DONE
            messages.success(request, f'Задача «{task.title}» отмечена как выполненная ✅')
        else:
            task.status = Task.Status.TODO
            messages.info(request, f'Задача «{task.title}» возвращена в работу 🔁')

        task.save(update_fields=['is_done', 'status'])
        return redirect('todo:task_list')


class TaskChangeView(LoginRequiredMixin, View):
    def post(self, request, pk, new_status):
        task = get_object_or_404(Task, pk=pk, user=request.user)
        if new_status in dict(Task.Status.choices):
            task.status = new_status
            task.save(update_fields=['status'])
            messages.success(self.request, f'Статус изменён на {task.get_status_display()}')
        return redirect('todo:task_list')


class TaskArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, user=request.user)
        task.is_archived = not task.is_archived
        task.status = Task.Status.ARCHIVED if task.is_archived else Task.Status.TODO
        task.save()
        messages.success(request, 'Задача архивирована' if task.is_archived else 'Задача восстановлена')
        return redirect('todo:task_list')


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'todo/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tasks = Task.objects.filter(user=self.request.user)
        ctx['total_tasks'] = tasks.count()
        ctx['completed_tasks'] = tasks.filter(status=Task.Status.DONE).count()
        ctx['pending_tasks'] = tasks.filter(status=Task.Status.TODO).count()
        ctx['in_progress_tasks'] = tasks.filter(status=Task.Status.IN_PROGRESS).count()
        ctx['recent_tasks'] = tasks.order_by('-created_at')[:5]
        return ctx


class DuplicateTaskView(LoginRequiredMixin, View):
    def post(self, request, pk):
        original = get_object_or_404(Task, pk=pk, user=request.user)
        duplicate = Task.objects.create(
            user=self.request.user,
            title=original.title,
            description=original.description,
            priority=original.priority,
            status=Task.Status.TODO,
        )
        messages.success(request, 'Задача дублирована')
        return  redirect('todo:task_detail', pk=duplicate.pk)
