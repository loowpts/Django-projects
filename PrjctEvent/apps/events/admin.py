from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

from .models import Category, Event, Review, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'event_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

    def event_count(self, obj):
        return obj.event_set.count()
    event_count.short_description = _('Количество событий')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1
    fields = ('user', 'rating', 'comment', 'approved', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = True

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff or (obj and obj.user == request.user)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'status', 'start_datetime', 'views_count', 'average_rating')
    list_filter = ('status', 'category', 'start_datetime', 'author')
    search_fields = ('title', 'description', 'author__username', 'author__email')
    date_hierarchy = 'start_datetime'
    ordering = ('-start_datetime',)
    readonly_fields = ('views_count', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'status')
        }),
        (_('Содержание'), {
            'fields': ('short_description', 'description', 'image')
        }),
        (_('Детали'), {
            'fields': ('category', 'tags', 'location', 'start_datetime', 'end_datetime', 'views_count')
        }),
    )
    inlines = [ReviewInline]
    actions = ['publish_events', 'draft_events']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_staff:
            qs = qs.filter(author=request.user)
        return qs.select_related('author', 'category').prefetch_related('tags', 'reviews')

    def average_rating(self, obj):
        agg = obj.reviews.aggregate(avg=models.Avg('rating'))['avg']
        return f"{agg:.1f}" if agg else _('Нет оценок')
    average_rating.short_description = _('Средний рейтинг')

    def publish_events(self, request, queryset):
        updated = queryset.update(status=Event.Status.PUBLISHED)
        messages.success(request, f'{updated} событий опубликовано.')
    publish_events.short_description = _('Опубликовать выбранные события')

    def draft_events(self, request, queryset):
        updated = queryset.update(status=Event.Status.DRAFT)
        messages.success(request, f'{updated} событий переведено в черновик.')
    draft_events.short_description = _('Перевести в черновик')

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        if not obj.slug:
            obj.slug = slugify(obj.title)
        super().save_model(request, obj, form, change)


    def has_change_permission(self, request, obj=None):
        if obj and not request.user.is_staff:
            return obj.author == request.user
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('event_link', 'user', 'rating', 'approved', 'created_at')
    list_filter = ('approved', 'rating', 'created_at')
    search_fields = ('event__title', 'user__username', 'user__email', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['approve_reviews', 'reject_reviews']
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event', 'user')

    def event_link(self, obj):
        url = reverse('admin:events_event_change', args=[obj.event.id])
        return '<a href="{}">{}</a>'.format(url, obj.event.title)
    event_link.allow_tags = True
    event_link.short_description = _('Событие')

    def approve_reviews(self, request, queryset):
        updated = queryset.update(approved=True)
        messages.success(request, f'{updated} отзывов одобрено.')
    approve_reviews.short_description = _('Одобрить выбранные отзывы')

    def reject_reviews(self, request, queryset):
        updated = queryset.update(approved=False)
        messages.success(request, f'{updated} отзывов отклонено.')
    reject_reviews.short_description = _('Отклонить выбранные отзывы')

    # Разрешения: только staff
    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff