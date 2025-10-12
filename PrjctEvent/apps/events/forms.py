from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from .models import Event, Review, Tag, Category
from django.db import transaction

def split_tags(tag_string):
    if not tag_string:
        return []
    return [t.strip() for t in tag_string.split(',') if t.strip()]

class EventForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_('Теги')
    )

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'short_description', 'category', 'tags',
            'image', 'start_datetime', 'end_datetime', 'location', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': _('Название события')}),
            'description': forms.Textarea(attrs={'rows': 5}),
            'short_description': forms.Textarea(attrs={'rows': 3}),
            'start_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'location': forms.TextInput(attrs={'placeholder': _('Место проведения или ссылка для онлайн')}),
        }
        labels = {
            'title': _('Название'),
            'description': _('Описание'),
            'short_description': _('Краткое описание'),
            'category': _('Категория'),
            'image': _('Изображение'),
            'start_datetime': _('Дата и время начала'),
            'end_datetime': _('Дата и время окончания'),
            'location': _('Местоположение'),
            'status': _('Статус'),
        }

        def __init__(self, *args, **kwargs):
            self.request = kwargs.pop('request', None)
            super().__init__(*args, **kwargs)
            self.fields['category'].queryset = Category.objects.all()

        def clean(self):
            cleaned = super().clean()
            start = cleaned.get('start_datetime')
            end = cleaned.get('end_datetime')
            if start and end:
                if end <= end:
                    raise ValidationError({
                        'end_datetime': _('Время окончания должно быть позже времени начала.')
                    })
            return cleaned

        def _get_or_create_tags(self, tag_names):
            tags = []
            for name in tag_names:
                name = name.strip()
                if not name:
                    continue
                slug = slugify(name)
                tag_obj = Tag.objects.get_or_create(slug=slug, defaults={'name': name})
                tags.append(tag_obj)
            return tags

        @transaction.atomic
        def save(self, commit=True):
            tag_string = self.cleaned_data.get('tag_list', '') if hasattr(self, 'cleaned_data') else ''
            event = super().save(commit=commit)

            tag_names = split_tags(tag_string)
            if tag_names:
                tags = self._get_or_create_tags(tag_names)
            else:
                event.tags.clear()
            return event


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'rating': _('Оцените события от 1 до 5.'),
            'text': _('Поделитесь впечатлениями.'),
        }

        def __init__(self, *args, **kwargs):
            """
            Принимаем user и event через kwargs — чтобы проверять уникальность.
            """
            self.user = kwargs.pop('user', None)
            self.event = kwargs.pop('event', None)
            super().__init__(*args, **kwargs)

        def clean(self):
            cleaned = super().clean()
            # Проверка: один отзыв от одного пользователя на событие
            if not self.instance.pk and self.user and self.event:
                exists = Review.objects.filter(user=self.user, event=self.event).exists()
                if exists:
                    raise ValidationError(_('Вы уже оставляли отзыв для этого события.'))
            return cleaned

        def save(self, commit=True):
            obj = super().save(commit=False)
            if self.user:
                obj.user = self.user
            if self.event:
                obj.event = self.event
            if commit:
                obj.save()
            return obj


class SearchForm(forms.Form):
    q = forms.CharField(
        label=_('Поиск'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Поиск по названию или описанию')})
    )
    category = forms.ModelChoiceField(
        label=_('Категория'),
        queryset=Category.objects.all(),
        required=False,
        empty_label=_('Все категории')
    )
    status = forms.ChoiceField(
        label=_('Статус'),
        choices=[('', _('Все статусы'))] + Event.Status.choices,
        required=False
    )


class EventArchiveForm(forms.Form):
    year = forms.ChoiceField(
        label=_('Год'),
        choices=[('', _('Все годы'))] + [(str(y), str(y)) for y in range(2020, 2026)],  # Настрой диапазон годов
        required=False
    )
    month = forms.ChoiceField(
        label=_('Месяц'),
        choices=[('', _('Все месяцы'))] + [
            ('1', _('Январь')), ('2', _('Февраль')), ('3', _('Март')),
            ('4', _('Апрель')), ('5', _('Май')), ('6', _('Июнь')),
            ('7', _('Июль')), ('8', _('Август')), ('9', _('Сентябрь')),
            ('10', _('Октябрь')), ('11', _('Ноябрь')), ('12', _('Декабрь'))
        ],
        required=False
    )