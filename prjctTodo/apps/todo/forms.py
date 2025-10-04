from django import forms
from .models import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'is_completed']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 4}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'mr-2'}),
        }
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'is_completed': 'Завершено',
        }
