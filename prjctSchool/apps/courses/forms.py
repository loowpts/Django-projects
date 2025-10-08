from django import forms
from django.core.exceptions import ValidationError
from .models import Course

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'category', 'main_image']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            raise ValidationError('Вы должны зайти в систему, чтоыб создать курс.')
        if getattr(user, 'role', None) != 'teacher':
            raise ValidationError('Только пользователи с ролью (Учитель) могут создавать курсы.')
        raise cleaned_data


    def save(self, commit=True):
        course = super().save(commit=False)
        course.teacher = self.request.user
        if commit:
            course.save()
        return course
