from typing import Any
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Ticket, Registration
from apps.events.models import Event


class TicketForm(forms.ModelForm):
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        label=_('Количество для покупки'),
        help_text=_('Сколько билетов купить (для пользователя).')
    )

    class Meta:
        model = Ticket
        fields = ['type', 'price', 'quantity_available']
        widgets = {
            'type': forms.Select(choices=Ticket.TicketType.choices),
        }
        labels = {
            'type': _('Тип билета'),
            'price': _('Цена'),
            'quantity_available': _('Доступно всего'),
        }

    def __init__(self, *args, event=None, **kwargs):
        self.event = event or kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        if self.event:
            existing_types = self.event.tickets.values_list('type', flat=True)
            choices = [(t, d) for t, d in Ticket.TicketType.choices if t not in existing_types]
            self.fields['type'].choices = choices
            self.fields['type'].help_text = _('Доступные типы для этого события.')
            
    def clean(self):
        cleaned_data = super().clean()
        type_ = cleaned_data.get('type')
        price = cleaned_data.get('price')
        qty_available = cleaned_data.get('quantity_available')
        qty_purchase = cleaned_data.get('quantity', 1)
        
        if price < 0:
            raise ValidationError(_('Цена не может быть отрицательной.'))

        if qty_available < 0:
            raise ValidationError(_('Доступное количество не может быть отрицательным.'))
        
        if self.instance.pk:
            available = self.instance.quantity_available - self.instance.sold_count
            if qty_purchase > available:
                raise ValidationError(_('Недостаточно билетов: доступно %(avail)s') % {'avail': available})

        if type == Ticket.TicketType.VIP and price <= 1000:
            self.add_error('price', _('VIP билет должен стоить больше 1000 руб.'))
        
        return cleaned_data
    
    def save(self, commit=True):
        ticket = super().save(commit=False)
        if self.event:
            ticket.event = self.event
        if commit:
            ticket.save()
        return ticket


class RegistrationForm(forms.ModelForm):
    ticket_type = forms.ChoiceField(
        choices=[],
        label=_('Тип билета'),
        help_text=_('Выберите тип. Для бесплатного события - автоматически.')
    )
    quantity = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=1,
        label=_('Количество'),
    )
    event = forms.ModelChoiceField(
        queryset=Event.objects.all(),
        widget=forms.HiddenInput(),
        label=_('Событие')
    )
    
    def __init__(self, *args, user=None, event=None, **kwargs):
        self.user = user or kwargs.pop('user', None)
        self.event = event or kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        if self.event:
            ticket_qs = Ticket.objects.filter(event=self.event)
            choices = [(ticket.type, f'{ticket.get_type_display()} - {ticket.price} руб.') for ticket in ticket_qs]
            if not choices:
                choices = [('', _('Нет доступных билетов.'))]
            self.fields['ticket_type'].choices = choices
            
            # Если событие бесплатное — скрыть/отключить цену
            if self.event.is_free():
                self.fields['ticket_type'].widget = forms.HiddenInput()
                self.fields['ticket_type'].initial = Ticket.TicketType.STANDARD
                self.fields['ticket_type'].required = False

    def clean(self):
        """Валидация: Если бесплатное — без цены; availability; дубли."""
        cleaned_data = super().clean()
        event = cleaned_data.get('event')
        ticket_type = cleaned_data.get('ticket_type')
        quantity = cleaned_data.get('quantity')

        if not event:
            raise ValidationError(_('Событие обязательно.'))

        # Проверка существующих регистраций (предотвратить дубли)
        if self.user:
            if Registration.objects.filter(user=self.user, event=event).exists():
                raise ValidationError(_('Вы уже зарегистрированы на это событие.'))

        # Для бесплатного события
        if event.is_free():
            if ticket_type:
                raise ValidationError(_('Для бесплатного события тип билета не нужен.'))
            cleaned_data['total_amount'] = 0  # Для view
            return cleaned_data

        # Для платного: проверка ticket_type и availability
        if not ticket_type:
            raise ValidationError(_('Выберите тип билета.'))

        ticket = Ticket.objects.get(event=event, type=ticket_type)
        if not ticket.is_available(quantity):
            raise ValidationError(_('Недостаточно билетов для выбранного типа.'))

        # Расчёт суммы (для Stripe в view)
        cleaned_data['total_amount'] = ticket.price * quantity
        cleaned_data['ticket'] = ticket  # Для сохранения в view

        return cleaned_data
                 
            
    
