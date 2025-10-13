from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Avg
from django.contrib import messages

from .models import Category, Tag, Event, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    list_per_page = 50


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    list_per_page = 50


class ReviewInline(admin.TabularInline):
    model = Review
    fields = ('user', 'rating', 'approved', 'created_at', 'text_preview')
    readonly_fields = ('created_at', 'text_preview')
    extra = 0
    show_change_link = True
    ordering = ('-created_at',)

    def text_preview(self, obj):
        # Краткий фрагмент текста отзыва
        if not obj.text:
            return '-'
        return (obj.text[:75] + '...') if len(obj.text) > 75 else obj.text

    text_preview.short_description = 'Текст (превью)'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author_link', 'category', 'start_datetime', 'status', 'views_count', 'average_rating_display', 'image_thumb'
    )
    list_filter = ('status', 'category', 'start_datetime', 'author')
    search_fields = ('title', 'description', 'short_description', 'location', 'author__username')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'views_count', 'image_thumb')
    inlines = [ReviewInline]
    date_hierarchy = 'start_datetime'
    ordering = ('-start_datetime',)
    list_select_related = ('author', 'category')
    filter_horizontal = ('tags',)
    list_per_page = 25

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'status', 'category', 'tags', 'image', 'image_thumb')
        }),
        ('Описание и время', {
            'fields': ('short_description', 'description', ('start_datetime', 'end_datetime'), 'location'),
        }),
        ('Системное', {
            'fields': ('views_count', 'created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(_avg_rating=Avg('reviews__rating'))
        return qs

    def average_rating_display(self, obj):
        avg = getattr(obj, '_avg_rating', None)
        if avg is None:
            return '-'
        # округлим до 2 знаков
        return f'{avg:.2f}'

    average_rating_display.short_description = 'Средний рейтинг'
    average_rating_display.admin_order_field = '_avg_rating'

    def image_thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:60px; max-width:120px; object-fit:cover;" />', obj.image.url)
        return '-'

    image_thumb.short_description = 'Превью'

    def author_link(self, obj):
        if obj.author:
            try:
                url = reverse('admin:auth_user_change', args=(obj.author.pk,))
                return format_html('<a href="{}">{}</a>', url, obj.author)
            except Exception:
                return str(obj.author)
        return '-'

    author_link.short_description = 'Автор'
    author_link.admin_order_field = 'author__username'


@admin.action(description='Одобрить выбранные отзывы')
def make_approved(modeladmin, request, queryset):
    updated = queryset.update(approved=True)
    modeladmin.message_user(request, f'Одобрено {updated} отзыв(ов).', level=messages.SUCCESS)


@admin.action(description='Отметить выбранные отзывы как не одобренные')
def make_unapproved(modeladmin, request, queryset):
    updated = queryset.update(approved=False)
    modeladmin.message_user(request, f'Обновлено {updated} отзыв(ов).', level=messages.SUCCESS)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'event_link', 'user', 'rating', 'approved', 'created_at')
    list_filter = ('approved', 'rating', 'created_at', 'event__category')
    search_fields = ('user__username', 'user__email', 'event__title', 'text')
    actions = [make_approved, make_unapproved]
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user', 'event')
    ordering = ('-created_at',)
    list_per_page = 40

    fields = ('event', 'event_link', 'user', 'rating', 'text', 'approved', 'created_at', 'updated_at')
    def event_link(self, obj):
        if obj.event:
            try:
                url = reverse('admin:events_event_change', args=(obj.event.pk,))
                return format_html('<a href="{}">{}</a>', url, obj.event.title)
            except Exception:
                return obj.event.title
        return '-'

    event_link.short_description = 'Событие'
