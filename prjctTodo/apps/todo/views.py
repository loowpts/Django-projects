from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Task
from .forms import TaskForm


@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user)
    return render(request, 'todo/task_list.html', {'tasks': tasks})


@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            return redirect('todo:task_list')
    else:
        form = TaskForm()
    return render(request, 'todo/task_form.html', {'form': form})


@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('todo:task_list')
    else:
        form = TaskForm(instance=task)
    return render(request, 'todo/task_form', {'form': form})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        task.delete()
        return redirect('todo:task_list')
    return render(request, 'todo/task_item.html', {'task': task})


@login_required
def task_toggle(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        task.is_completed = not task.is_completed
        task.save()
        return redirect('todo:task_list')
    return render(request, 'todo/task_list.html', {'task': task})
