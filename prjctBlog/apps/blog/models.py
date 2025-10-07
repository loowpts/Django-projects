from django.db import models
from apps.users.models import User
from django.utils.text import slugify
from taggit.managers import TaggableManager
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(_('Название'),  max_length=150, unique=True)
    slug = models.SlugField(_('Слаг'), max_length=150, unique=True)

    class Meta:
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name=_('Автор'))
    title = models.CharField(_('Заголовок'), max_length=150)
    slug = models.SlugField(_('Слаг'), unique=True)
    short_description = models.CharField(_("Краткое описание"), max_length=300, blank=True)
    body = models.TextField(_('Текст статьи'))
    status = models.CharField(_('Статус'),max_length=10, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(_('Дата публикации'), null=True, blank=True)
    cover_image = models.ImageField(_('Главное изображение'), upload_to='posts/covers', null=True, blank=True)
    views_count = models.PositiveIntegerField(_("Количество просмотров"), default=0)
    created_at = models.DateTimeField(_('Создано'),auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_('Категория')
    )
    tags = TaggableManager(blank=True, verbose_name=_('Тэги'))

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            count = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED


class Comment(models.Model):
    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Пост')
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.SET_NULL,
        null=True,
        blank=True,
        related_name='comments',
        verbose_name=_('Автор')
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='replies'
        verbose_name=_('Родительский комментарий')
    )
    body = models.TextField()
    author_name = models.CharField(max_length=100, blank=True,
                                   help_text='Используется, если комментарий оставлен анонимно')
    is_public = models.BooleanField(_('Публичный'), default=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comment by {self.display_author} on {self.post.title[:20]}'

    @property
    def display_author(self):
        if self.author:
            return self.author.get_username()
        return self.author_name or "Anonymous"

    @property
    def is_reply(self):
        return self.parent is not None


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'))
    post = models.ForeignKey(Post, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_('Пост'))
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_('Комментарий'))
    value = models.IntegerField(default=1)
    created_at = models.DateTimeField(_('Создано'),auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post', 'comment')


class Subscription(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='subscriptions', verbose_name=_('Пользователь')
        )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Категория')
        )
    created_at = models.DateTimeField(_('Создано'),auto_now_add=True)

    class Meta:
        unique_together = ('user', 'category')
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user} -> {self.category}'
    
    @staticmethod
    def is_subscribed(user, category):
        return Subscription.objects.filter(user=user, category=category).exists()
