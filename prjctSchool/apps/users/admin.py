from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = _('профили')
    fields = ('avatar', 'bio', 'date_of_birth', 'is_public', 'timezone', 'streak_visibility')
    readonly_fields = ('avatar',)


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('email', 'full_name', 'role', 'is_active', 'is_staff', 'is_verified', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'is_verified')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    readonly_fields = ('date_joined', 'updated_at', 'last_login')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Личная информация'), {'fields': ('first_name', 'last_name', 'role')}),
        (_('Статус'), {'fields': ('is_active', 'is_verified')}),
        (_('Права доступа'), {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Важные даты'), {'fields': ('last_login', 'date_joined', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
    )

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = _('ФИО')


admin.site.register(User, CustomUserAdmin)
