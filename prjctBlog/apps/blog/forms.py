from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Post, Comment, Category, Like


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Название категории"}),
            "slug": forms.TextInput(attrs={"placeholder": "slug"}),
        }


class PostForm(forms.ModelForm):
    """
    ModelForm для Post.
    - published_at выводится/принимается через datetime-local widget.
    - tags обрабатываются автоматически django-taggit (поле доступно в форме).
    """
    published_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"],
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "short_description",
            "body",
            "category",
            "tags",
            "status",
            "published_at",
            "cover_image",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Заголовок поста"}),
            "short_description": forms.Textarea(attrs={"rows": 2}),
            "body": forms.Textarea(attrs={"rows": 12, "placeholder": "Markdown или HTML"}),
            "tags": forms.TextInput(attrs={"placeholder": "django, python, backend (через запятую)"}),
            "cover_image": forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        """
        Если передается instance с published_at, приводим его в формат, понятный datetime-local.
        """
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.published_at:
            # формат: YYYY-MM-DDTHH:MM (поддерживается большинством браузеров)
            self.initial["published_at"] = self.instance.published_at.strftime("%Y-%m-%dT%H:%M")

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        # можно позволить пустой slug (автогенерация в модели), но если задан — проверить уникальность
        if slug:
            qs = Post.objects.filter(slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Slug уже используется.")
        return slug

    def clean(self):
        """
        Если статус = published и published_at не заполнен, ставим текущее время.
        """
        cleaned = super().clean()
        status = cleaned.get("status")
        published_at = cleaned.get("published_at")

        if status == Post.Status.PUBLISHED and not published_at:
            cleaned["published_at"] = timezone.now()
        return cleaned

    def save(self, commit=True):
        """
        Важно: при использовании в CreateView/UpdateView в form_valid ставьте form.instance.author = request.user
        Если вы сохраняете с commit=False — не забудьте вызвать form.save_m2m() после save().
        """
        obj = super().save(commit=commit)
        return obj


class CommentForm(forms.ModelForm):
    parent = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Comment
        fields = ["body", "author_name", "parent"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "Написать комментарий..."}),
            "author_name": forms.TextInput(attrs={"placeholder": "Ваше имя (если не в аккаунте)"}),
        }

    def clean(self):
        data = super().clean()
        user = getattr(self, "initial", {}).get("request_user") or self.initial.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            if not data.get("author_name"):
                raise ValidationError("Укажите имя или авторизуйтесь.")
        return data


class LikeForm(forms.ModelForm):
    class Meta:
        model = Like
        fields = ['value']
