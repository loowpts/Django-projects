import stripe
import logging
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
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

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

class PurchaseView(LoginRequiredMixin, View):
    template_name = 'tickets/ticket_purchase.html'

    def get(self, request, event_slug):
        logger.info(f"PurchaseView.get: event_slug={event_slug}")
        event = get_object_or_404(Event, slug=event_slug)
        form = RegistrationForm(event=event, user=request.user)
        context = {'form': form, 'event': event}
        return TemplateResponse(request, self.template_name, context)

    def post(self, request, event_slug):
        logger.info(f"PurchaseView.post: event_slug={event_slug}")
        event = get_object_or_404(Event, slug=event_slug)
        form = RegistrationForm(data=request.POST, event=event, user=request.user)
        if form.is_valid():
            logger.info(f"Form valid: {form.cleaned_data}")
            with transaction.atomic():
                registration = form.save()
                if registration.ticket:
                    try:
                        logger.info("Creating Stripe session")
                        success_url = request.build_absolute_uri(
                            reverse('tickets:success', kwargs={'registration_id': registration.id})
                        ) + '?session_id={CHECKOUT_SESSION_ID}'
                        logger.info(f"Success URL: {success_url}")
                        session = stripe.checkout.Session.create(
                            payment_method_types=['card'],
                            line_items=[{
                                'price_data': {
                                    'currency': 'rub',
                                    'product_data': {
                                        'name': f'{registration.ticket.get_type_display()} - {event.title}',
                                    },
                                    'unit_amount': int(registration.ticket.price * 100),
                                },
                                'quantity': registration.quantity,
                            }],
                            mode='payment',
                            success_url=success_url,
                            cancel_url=request.build_absolute_uri(
                                reverse('tickets:cancel', kwargs={'registration_id': registration.id})
                            ),
                            metadata={'registration_id': str(registration.id)},
                            idempotency_key=f'registration_{registration.id}'
                        )
                        logger.info(f"Stripe session created: ID={session.id}, URL={session.url}")
                        registration.payment_id = session.id
                        registration.save()
                        send_ticket_email.delay(registration.id)
                        return redirect(session.url)
                    except stripe.StripeError as e:
                        logger.error(f"Stripe error: {str(e)}")
                        messages.error(request, _('Ошибка платежа. Попробуйте снова.'))
                        registration.delete()
                        return redirect('tickets:purchase', event_slug=event.slug)
                else:
                    registration.status = Registration.Status.CONFIRMED
                    registration.save()
                    notification = Notification.objects.create(
                        user=request.user,
                        title=f"Регистрация на {event.title}",
                        message=f"Вы зарегистрированы на событие '{event.title}'.",
                        event=event,
                        notification_type='REGISTRATION'
                    )
                    send_notification_email.delay(notification.id)
                    send_ticket_email.delay(registration.id)
                    messages.success(request, _('Регистрация прошла успешно!'))
                    return redirect('tickets:my_tickets')
        logger.error(f"Form errors: {form.errors}")
        messages.error(request, _('Ошибка. Проверьте данные.'))
        context = {'form': form, 'event': event}
        return TemplateResponse(request, self.template_name, context)


class RegisterView(LoginRequiredMixin, View):
    def post(self, request, event_slug):
        logger.info(f"RegisterView.post: event_slug={event_slug}")
        event = get_object_or_404(Event, slug=event_slug)
        form = RegistrationForm(data=request.POST, event=event, user=request.user)
        if form.is_valid():
            logger.info("Form is valid")
            with transaction.atomic():
                registration = form.save()
                registration.status = Registration.Status.CONFIRMED
                registration.save()
                notification = Notification.objects.create(
                    user=request.user,
                    title=f'Регистрация на {event.title}',
                    message=f'Вы зарегистрированы на событие ({event.title})',
                    event=event,
                    notification_type='REGISTRATION'
                )
                send_notification_email.delay(notification.id)
                send_ticket_email.delay(registration.id)
                messages.success(request, _('Регистрация прошла успешно!'))
                return redirect('tickets:my_tickets')
        logger.error(f"Form errors: {form.errors}")
        messages.error(request, _('Ошибка регистрации. Проверьте данные.'))
        return redirect('events:event_detail', slug=event_slug)


class UserTickets(LoginRequiredMixin, View):
    model = Registration
    template_name = 'tickets/my_tickets.html'
    context_object_name = 'registrations'

    def get(self, request):
        registrations = Registration.objects.filter(user=self.request.user).select_related('event', 'ticket')
        context = {'registrations': registrations}
        return TemplateResponse(request, self.template_name, context)


class SuccessView(View):
    def get(self, request, registration_id):
        logger.info(f"SuccessView.get: registration_id={registration_id}")
        registration = get_object_or_404(Registration, id=registration_id, user=request.user)
        if registration.status == Registration.Status.CONFIRMED:
            logger.info("Payment already confirmed")
            messages.success(request, _('Платёж уже подтверждён.'))
        else:
            session_id = request.GET.get('session_id')
            logger.info(f"Session ID from URL: {session_id}")
            if not session_id or session_id == '{CHECKOUT_SESSION_ID}':
                logger.error("Invalid or missing session_id")
                messages.error(request, _('Ошибка: отсутствует или неверный ID сессии.'))
                return TemplateResponse(request, 'tickets/success.html', {'registration': registration})
            try:
                logger.info(f"Retrieving Stripe session: {session_id}")
                session = stripe.checkout.Session.retrieve(session_id)
                if session.metadata['registration_id'] == str(registration.id):
                    with transaction.atomic():
                        registration.confirm(session.payment_intent)
                        notification = Notification.objects.create(
                            user=registration.user,
                            title=f'Покупка билета на {registration.event.title}',
                            message=f'Ваш билет на {registration.event.title} подтверждён.',
                            event=registration.event,
                            notification_type='TICKET'
                        )
                        send_notification_email.delay(notification.id)
                        send_ticket_email.delay(registration.id)
                        logger.info("Payment confirmed")
                        messages.success(request, _('Платёж подтверждён.'))
                else:
                    logger.error("Session metadata does not match registration ID")
                    messages.error(request, _('Ошибка: неверный ID сессии.'))
            except stripe.StripeError as e:
                logger.error(f"Stripe error: {str(e)}")
                messages.error(request, _('Ошибка проверки платежа.'))
        context = {'registration': registration}
        if request.headers.get('HX-Request'):
            logger.info("Returning HTMX response")
            return TemplateResponse(request, 'tickets/success_content.html', context)
        return TemplateResponse(request, 'tickets/success.html', context)


class CancelView(View):
    def get(self, request, registration_id):
        logger.info(f"CancelView.get: registration_id={registration_id}")
        registration = get_object_or_404(Registration, id=registration_id, user=request.user)
        if registration.status == Registration.Status.PENDING:
            registration.cancel()
            logger.info("Payment cancelled")
            messages.info(request, _('Платёж отменён.'))
        context = {'registration': registration}
        if request.headers.get('HX-Request'):
            logger.info("Returning HTMX response")
            return TemplateResponse(request, 'tickets/cancel_content.html', context)
        return TemplateResponse(request, 'tickets/cancel.html', context)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    logger.info("Stripe webhook received")
    if not hasattr(settings, 'STRIPE_WEBHOOK_SECRET'):
        logger.warning("STRIPE_WEBHOOK_SECRET not set, skipping webhook")
        return HttpResponse(status=200)
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.StripeError) as e:
        logger.error(f"Webhook error: {str(e)}")
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        registration_id = session['metadata']['registration_id']
        logger.info(f"Processing checkout.session.completed for registration_id: {registration_id}")
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
                logger.info("Webhook processed successfully")
        except Registration.DoesNotExist:
            logger.error("Registration not found")
            return HttpResponse(status=400)
    return HttpResponse(status=200)
