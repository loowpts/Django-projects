from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    model = Review
    fields = ['rating', 'comment']
    widgets = {
        'rating': forms.NumberInput(attrs={
            'min': 1,
            'max': 5,
            'class': 'form-control'
        }),
        'comment': forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Поделитесь своими впечатлениями...'
        }),
        }
