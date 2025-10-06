from django import forms
from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'status', 'is_done', 'is_archived']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded',
                'placeholder': 'Введите название задачи',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full p-2 border rounded',
                'rows': 4,
                'placeholder': 'Опишите задачу...',
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full p-2 border rounded',
            }),
            'status': forms.Select(attrs={
                'class': 'w-full p-2 border rounded',
            }),
            'is_done': forms.CheckboxInput(attrs={
                'class': 'mr-2',
            }),
            'is_archived': forms.CheckboxInput(attrs={
                'class': 'mr-2',
            }),
        }
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'priority': 'Приоритет',
            'status': 'Статус',
            'is_done': 'Завершено',
            'is_archived': 'Архивировать',
        }
