from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Post, Comment, Like, Subscription


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'posts_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def posts_count(self, obj):
        return obj.posts.count()
    posts_count.short_description = 'Количество постов'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'status', 'views_count', 'published_at', 'created_at']
    list_filter = ['status', 'category', 'created_at', 'published_at']
    search_fields = ['title', 'body', 'author__username']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    readonly_fields = ['views_count', 'created_at', 'updated_at', 'cover_preview']
    filter_horizontal = ['tags']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('author', 'title', 'slug', 'short_description', 'body')
        }),
        ('Категория и теги', {
            'fields': ('category', 'tags')
        }),
        ('Публикация', {
            'fields': ('status', 'published_at')
        }),
        ('Изображение', {
            'fields': ('cover_image', 'cover_preview')
        }),
        ('Статистика', {
            'fields': ('views_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="max-height: 200px; max-width: 300px;" />', obj.cover_image.url)
        return "Нет изображения"
    cover_preview.short_description = 'Превью обложки'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['short_body', 'display_author', 'post', 'is_public', 'is_reply', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['body', 'author__username', 'author_name', 'post__title']
    readonly_fields = ['created_at', 'display_author']
    raw_id_fields = ['post', 'author', 'parent']
    
    fieldsets = (
        ('Комментарий', {
            'fields': ('post', 'body', 'is_public')
        }),
        ('Автор', {
            'fields': ('author', 'author_name', 'display_author')
        }),
        ('Ответ', {
            'fields': ('parent',)
        }),
        ('Информация', {
            'fields': ('created_at',)
        }),
    )
    
    def short_body(self, obj):
        return obj.body[:50] + '...' if len(obj.body) > 50 else obj.body
    short_body.short_description = 'Текст'


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'comment', 'value', 'created_at']
    list_filter = ['value', 'created_at']
    search_fields = ['user__username', 'post__title']
    raw_id_fields = ['user', 'post', 'comment']
    readonly_fields = ['created_at']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['user__username', 'category__name']
    raw_id_fields = ['user', 'category']
    readonly_fields = ['created_at']
