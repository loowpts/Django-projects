from celery import shared_task
from django.core.mail import EmailMessage
from weasyprint import HTML
from io import BytesIO
from .models import Registration
from django.conf import settings


@shared_task
def send_ticket_email(registration_id):
    registration = Registration.objects.get(id=registration_id)
    subject = f"Ваш билет на {registration.event.title}"
    message = f"Спасибо за покупку билета на '{registration.event.title}'!"
    email = EmailMessage(
        subject, message, settings.DEFAULT_FROM_EMAIL, [registration.user.email]
    )
    
    html_content = f"""
    <h1>Билет на {registration.event.title}</h1>
    <p>Пользователь: {registration.user.email}</p>
    <p>Тип: {registration.ticket.get_type_display() if registration.ticket else 'Бесплатно'}</p>
    <p>Количество: {registration.quantity}</p>
    """
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    email.attach(f'ticket_{registration.id}.pdf', pdf_file.getvalue(), 'application/pdf')
    email.send()
