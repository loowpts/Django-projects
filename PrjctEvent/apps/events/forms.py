from django import forms
from .models import Event, Review, Category, Tag


class EventForm(forms.ModelForm):
    tag_list = forms.CharField(
        required=False,
        max_length=500,
        help_text='Введите теги через запятую для создания новых',
        widget=forms.TextInput(attrs={
            'placeholder': 'например: музыка, концерт, рок'
        })
    )
    
    class Meta:
        model = Event
        fields = ['title', 'short_description', 'description', 'category', 
                  'start_datetime', 'end_datetime', 'location', 'image', 'tags', 'status']
        widgets = {
            'start_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={'rows': 5}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'tags': forms.CheckboxSelectMultiple(),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.instance.pk:
            self.fields['tag_list'].initial = ', '.join(
                tag.name for tag in self.instance.tags.all()
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
        
        # Обработка новых тегов из tag_list
        tag_list = self.cleaned_data.get('tag_list', '')
        if tag_list:
            tag_names = [name.strip() for name in tag_list.split(',') if name.strip()]
            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(name=tag_name)
                instance.tags.add(tag)
        
        return instance


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'min': 1,
                'max': 5,
                'class': 'form-control'
            }),
            'text': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Поделитесь своими впечатлениями...'
            }),
        }


class EventSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Поиск событий...',
            'class': 'form-control'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='Все категории',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    tag = forms.ModelChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        empty_label='Все теги',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class EventArchiveForm(forms.Form):
    year = forms.IntegerField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    month = forms.IntegerField(
        required=False,
        widget=forms.Select(
            choices=[(i, i) for i in range(1, 13)],
            attrs={'class': 'form-control'}
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone
        current_year = timezone.now().year
        year_choices = [(year, year) for year in range(2020, current_year + 2)]
        self.fields['year'].widget = forms.Select(
            choices=[('', 'Все годы')] + year_choices,
            attrs={'class': 'form-control'}
        )
