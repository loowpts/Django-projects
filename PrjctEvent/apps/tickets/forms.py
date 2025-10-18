from typing import Any
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Ticket, Registration
from apps.events.models import Event
import logging


logger = logging.getLogger(__name__)


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


class RegistrationForm(forms.Form):
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
    
    def __init__(self, *args, user=None, event=None, **kwargs):
        self.user = user or kwargs.pop('user', None)
        self.event = event or kwargs.pop('event', None)
        super().__init__(*args, **kwargs)

        if self.event:
            ticket_qs = Ticket.objects.filter(event=self.event)
            logger.info(f"Tickets for event {self.event.slug}: {ticket_qs.count()}")
            choices = [(ticket.type, f'{ticket.get_type_display()} - {ticket.price} руб.') for ticket in ticket_qs]
            if not choices:
                choices = [('', _('Нет доступных билетов.'))]
            self.fields['ticket_type'].choices = choices

            if self.event.is_free:
                self.fields['ticket_type'].choices = [('', 'Стандартный (бесплатно)')]
                self.fields['ticket_type'].widget = forms.HiddenInput()
                self.fields['ticket_type'].initial = ''
                self.fields['ticket_type'].required = False

    def clean(self):
        cleaned_data = super().clean()
        ticket_type = cleaned_data.get('ticket_type')
        quantity = cleaned_data.get('quantity')
        logger.info(f"Cleaning form: ticket_type={ticket_type}, quantity={quantity}")

        if not self.event:
            raise ValidationError(_('Событие обязательно.'))

        if self.user and Registration.objects.filter(user=self.user, event=self.event).exists():
            raise ValidationError(_('Вы уже зарегистрированы на это событие.'))

        if self.event.is_free:
            cleaned_data['total_amount'] = 0
            cleaned_data['ticket'] = None
            return cleaned_data

        if not ticket_type:
            raise ValidationError(_('Выберите тип билета.'))

        try:
            ticket = Ticket.objects.get(event=self.event, type=ticket_type)
        except Ticket.DoesNotExist:
            raise ValidationError(_('Выбранный тип билета недоступен.'))

        if not ticket.is_available(quantity):
            raise ValidationError(_('Недостаточно билетов для выбранного типа.'))

        cleaned_data['total_amount'] = ticket.price * quantity
        cleaned_data['ticket'] = ticket
        return cleaned_data

    def save(self, commit=True):
        logger.info("Saving registration")
        registration = Registration.objects.create(
            user=self.user,
            event=self.event,
            ticket=self.cleaned_data['ticket'],
            quantity=self.cleaned_data['quantity'],
            total_amount=self.cleaned_data['total_amount'],
            status=Registration.Status.PENDING if self.cleaned_data['ticket'] else Registration.Status.CONFIRMED
        )
        logger.info(f"Registration saved: ID={registration.id}")
        return registration
                 
            
    
