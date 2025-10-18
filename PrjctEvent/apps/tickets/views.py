from django.db.models.query import QuerySet
from django.forms import BaseModelForm
import stripe
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, View, ListView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.response import TemplateResponse
from django.http import HttpResponse
from .models import Ticket, Registration
from .forms import RegistrationForm
from apps.events.models import Event
from apps.notifications.tasks import send_notification_email
from apps.notifications.models import Notification
from .tasks import send_ticket_email

stripe.api_key = settings.STRIPE_SECRET_KEY


class PurchaseView(LoginRequiredMixin, CreateView):
    form_class = RegistrationForm
    template_name = 'tickets/ticket_purchase.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        event = get_object_or_404(Event, slug=self.kwargs['event_slug'])
        kwargs['event'] = event
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        event = form.cleaned_data['event']
        if event.is_free():
            return redirect('tickets:register', event_slug=event.slug)
        
        ticket = form.cleaned_data['ticket']
        quantity = form.cleaned_data['quantity']
        total_amount = form.cleaned_data['total_amount']
        
        # Create Registration (pending)
        registration = Registration.objects.create(
            user=self.request.user,
            event=event,
            ticket=ticket,
            quantity=quantity,
            total_amount=total_amount,
            status=Registration.Status.PENDING
        )
        
        # Check session
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'rub',
                        'product_data': {
                            'name': f'{ticket.get_type_display()} - {event.title}',
                        },
                        'unit_amount': int(ticket.price * 100),
                    },
                    'quantity': quantity,
                }],
                mode='payment',
                success_url=self.request.build_absolute_uri(
                    reverse('tickets:success', kwargs={'registration_id': registration.id}) + '?session_id={CHECKOUT_SESSION_ID}'
                ),
                cancel_url=self.request.build_absolute_uri(
                    reverse('tickets:cancel', kwargs={'registration_id': registration.id})
                ),
                metadata={'registration_id': str(registration.id)},
                idempotency_key=f'registration_{registration.id}'
            )
            registration.payment_id = session.id
            registration.save()
            send_ticket_email.delay(registration.id)
            return redirect(session.url)
        except stripe.error.StripeError as e:
            messages.error(self.request, 'Ошибка платежка. Попробуйте снова.')
            registration.delete()
            return self.form_invalid(form)


class RegisterView(LoginRequiredMixin, View):
    def post(self, request, event_slug):
        event = get_object_or_404(Event, slug=event_slug)
        form = RegistrationForm(data=request.POST, event=event, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                registration = Registration.objects.create(
                    user=request.user,
                    event=event,
                    ticket=None,
                    quantity=form.cleaned_data['quantity'],
                    total_amount=0,
                    status=Registration.Status.CONFIRMED
                )
                notification = Notification.objects.create(
                    user=request.user,
                    title=f'Регистрация на {event.title}',
                    message=f'Вы зарегистрированы на событие ({event.title})',
                    notification_type='REGISTRATION'
                )
                send_notification_email.delay(notification.id)
                send_ticket_email.delay(registration.id)
                messages.success(request, 'Регистрация прошла успешно!')
                return redirect('tickets:my_tickets')
            messages.error(request, 'Ошибка регистрации. Проверьте данные.')
            return redirect('events:event_detail', slug=event_slug)


class UserTickets(LoginRequiredMixin, ListView):
    model = Registration
    template_name = 'tickets/my_tickets.html'
    context_object_name = 'registrations'
    
    def get_queryset(self):
        return Registration.objects.filter(user=self.request.user).select_related('event', 'ticket')
    
    
class SuccessView(View):
    def get(self, request, registration_id):
        registration = get_object_or_404(Registration, id=registration_id, user=request.user)
        
        if registration.status == Registration.Status.CONFIRMED:
            messages.success(request, 'Платеж уже подтвержден.')
        else:
            session_id = request.GET.get('session_id')
            if session_id:
                try:
                    session = stripe.checkout.Session.retrieve(session_id)
                    if session.metadata['registration_id'] == str(registration.id):
                        with transaction.atomic():
                            registration.confirm(session.payment_intent)
                            notification = Notification.objects.create(
                                user=request.user,
                                title=f'Покупка билета на ({registration.event.title})',
                                message=f'Ваш билет на ({registration.event.title}) подтвержден.',
                                event=registration.event,
                                notification_type='TICKET'
                            )
                            send_notification_email.delay(notification.id)
                            send_ticket_email.delay(registration.id)
                            messages.success(request, 'Платеж подтвержден.')
                except stripe.error.StripeError:
                    messages.error(request, 'Ошибка проверки платежа.')
            
            context = {'registration': registration}
            if request.headers.get('HX-Request'):
                return TemplateResponse(request, 'tickets/success_content.html', context)
            return TemplateResponse(request, 'tickets/success.html', context)
        

class CancelView(View):
    def get(self, request, registration_id):
        registration = get_object_or_404(Registration, id=registration_id, user=request.user)
        if registration.status == Registration.Status.PENDING:
            registration.cancel()
            messages.info(request, 'Платеж отменен.')
        context = {'registration': registration}
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'tickets/cancel_content.html', context)
        return TemplateResponse(request, 'tickets/cancel.html', context)            
        
                      
@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        registration_id = session['metadata']['registration_id']
        try:
            registration = Registration.objects.get(id=registration_id)
            with transaction.atomic():
                registration.confirm(session.payment_intent)
                notification = Notification.objects.create(
                    user=registration.user,
                    title=f"Покупка билета на {registration.event.title}",
                    message=f"Ваш билет на {registration.event.title} подтверждён.",
                    event=registration.event,
                    notification_type='TICKET'
                )
                send_notification_email.delay(notification.id)
                send_ticket_email.delay(registration.id)
        except Registration.DoesNotExist:
            return HttpResponse(status=400)
    return HttpResponse(status=200)
