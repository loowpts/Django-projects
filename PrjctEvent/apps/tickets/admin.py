from django.contrib import admin
from .models import Ticket, Registration


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 1


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'ticket', 'status', 'purchase_date']
    list_filter = ['status', 'event']
    search_fields = ['user__email', 'event__title']
    actions = ['cancel_registrations']

    def cancel_registrations(self, request, queryset):
        for reg in queryset:
            reg.cancel()
        self.message_user(request, "Регистрации отменены.")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['event', 'type', 'price', 'quantity_available', 'sold_count']
    list_filter = ['event', 'type']
