from django import forms
from .models import Notification


class NotificationFilterForm(forms.Form):
    IS_READ_CHOICES = [
        ('', 'Все'), 
        ('true', 'Прочитанные'), 
        ('false', 'Непрочитанные')
    ]

    is_read = forms.ChoiceField(
        choices=IS_READ_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    notification_type = forms.ChoiceField(
        choices=[('', 'Все')] + Notification.NOTIFICATION_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

