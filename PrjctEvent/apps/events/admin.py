from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Category, Tag, Event, Review


# Админка для Category
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name',)
    ordering = ['name']

admin.site.register(Category, CategoryAdmin)


# Админка для Tag
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name',)
    ordering = ['name']

admin.site.register(Tag, TagAdmin)


# Админка для Event
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'category', 'author', 'status', 'start_datetime', 'end_datetime', 'views_count', 'created_at', 'updated_at'
    )
    list_filter = ('status', 'category', 'author', 'start_datetime', 'end_datetime', 'tags')
    search_fields = ('title', 'description', 'slug', 'author__username')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-start_datetime']

    def average_rating(self, obj):
        return obj.average_rating() or _('Нет отзывов')

    average_rating.short_description = _('Средний рейтинг')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('tags', 'reviews')

admin.site.register(Event, EventAdmin)


# Админка для Review
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'rating', 'approved', 'created_at', 'updated_at')
    list_filter = ('approved', 'rating', 'event', 'user')
    search_fields = ('user__username', 'event__title', 'text')
    list_editable = ('approved',)
    ordering = ['-created_at']
    actions = ['approve_reviews', 'reject_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(approved=True)

    def reject_reviews(self, request, queryset):
        queryset.update(approved=False)

    approve_reviews.short_description = _('Одобрить выбранные отзывы')
    reject_reviews.short_description = _('Отклонить выбранные отзывы')

admin.site.register(Review, ReviewAdmin)
