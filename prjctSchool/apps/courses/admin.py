from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Category, Course, Lesson


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name',)

    fieldsets = (
        (None, {
            'fields': ('name', 'slug')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('courses')


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1
    show_change_link = True
    fields = ('title', 'content', 'order')
    ordering = ('order',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'teacher', 'created_at', 'lesson_count')
    list_filter = ('category', 'teacher', 'created_at')
    search_fields = ('title', 'description', 'teacher__username')
    list_select_related = ('category', 'teacher')
    inlines = [LessonInline]

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'category', 'teacher', 'main_image')
        }),
    )

    def lesson_count(self, obj):
        return obj.lessons.count()

    lesson_count.short_description = _('Количество уроков')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('lessons')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('title', 'content', 'course__title')
    list_select_related = ('course',)

    fieldsets = (
        (None, {
            'fields': ('course', 'title', 'content', 'order')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course')