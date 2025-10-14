from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.events.models import Event
from django.conf import settings


class Ticket(models.Model):
    class TicketType(models.TextChoices):
        STANDARD = 'standard', _('Стандартный')
        VIP = 'vip', _('VIP')

    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name=_('Событие')
    )
    type = models.CharField(
        max_length=20,
        choices=TicketType.choices,
        default=TicketType.STANDARD,
        verbose_name=_('Тип билета')
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name=_('Цена')
    )
    quantity_available = models.PositiveIntegerField(default=100, verbose_name=_('Доступное количество'))
    sold_count = models.PositiveIntegerField(default=0, editable=False, verbose_name=_('Продано'))

    class Meta:
        unique_together = ('event', 'type')
        verbose_name = _('Билет')
        verbose_name_plural = _('Билеты')
        indexes = [models.Index(fields=['event', 'type'])]

    def __str__(self):
        return f'{self.get_type_display()} - {self.event.title} ({self.price} руб.)'

    def clean(self):
        if self.price < 0:
            raise ValidationError('Цена не может быть отрицательной.')
        if self.sold_count > self.quantity_available:
            raise ValidationError('Продано больше, чем доступно')

    def is_available(self, qty=1):
        return (self.quantity_available - self.sold_count) >= qty

    @transaction.atomic
    def sell(self, qty=1):
        if not self.is_available(qty):
            raise ValueError('Недостаточно билетов.')
        self.sold_count += qty
        self.save(update_fields=['sold_count'])

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Registration(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Ожидает оплаты')
        CONFIRMED = 'confirmed', _('Подтверждено')
        CANCELLED = 'cancelled', _('Отменено')
        REFUNDED = 'refunded', _('Возвращено')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='registrations',
        verbose_name=_('Пользователь')
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='registrations',
        verbose_name=_('События')
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.SET_NULL,
        related_name='registrations',
        null=True,
        blank=True,
        verbose_name=_('Билет')
    )
    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Количество')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('Статус')
    )
    purchase_date = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата покупки/Регистрации'))
    payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('ID платежа')
    )
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, editable=False, verbose_name=_('Итого'))

    class Meta:
        unique_together = ('user', 'ticket')
        verbose_name = _('Регистрация')
        verbose_name_plural = _('Регистрации')
        indexes = [models.Index(fields=['user', 'event', 'status'])]
        permissions = [
            ('view_own_registrations', 'Can view own registrations'),
        ]

    def __str__(self):
        return f'{self.user} - {self.event.user} ({self.status})'

    def clean(self):
        if self.ticket and self.ticket.price > 0 and not self.ticket.payment_id:
            raise ValidationError('Для платного билета нужен payment_id')
        if self.quantity < 1:
            raise ValidationError('Количество должно быть больше нуля.')
        if self.ticket and not self.ticket.is_available(self.quantity):
            raise ValidationError('Недостаточно билетов.')

    @transaction.atomic
    def confirm(self, payment_id=None):
        if self.status != Status.PENDING:
            raise ValidationError('Уже обработано.')
        self.status = Status.CONFIRMED
        if payment_id:
            self.payment_id = payment_id
        if self.ticket:
            self.ticket.sell(self.quantity)
            self.total_amount = self.ticket.price * self.quantity
        self.save()

    @transaction.atomic
    def cancel(self, payment_id=None):
        if self.status == Status.CONFIRMED and self.ticket:
            self.ticket.sold_count = models.F('sold_count') - self.quantity
            self.ticket.save()
        self.status = Status.CANCELLED
        self.save()

    def save(self, *args, **kwargs):
        self.clean()
        if not self.total_amount and self.ticket:
            self.total_amount = self.ticket.price * self.quantity
        super().save(*args, **kwargs)