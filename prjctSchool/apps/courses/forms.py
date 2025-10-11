from django import forms
from django.core.exceptions import ValidationError
from .models import Course, Category

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


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']


class CourseSearchForm(forms.Form):
    query = forms.CharField(
        label='Поиск',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Введите название курса...',
            'class': 'form-control',
        }),
    )
    category = forms.ModelChoiceField(
        label='Категория',
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Lesson

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'content', 'order']
        labels = {
            'title': _('Заголовок'),
            'content': _('Контент'),
            'order': _('Порядок'),
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }