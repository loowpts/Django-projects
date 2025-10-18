from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_welcome_email_async(user_email, user_first_name):
    send_mail(
        subject='Добро пожаловать!',
        message=f'Привет, {user_first_name}! Спасибо за регистрацию.',
        from_email='твой_email@gmail.com',
        recipient_list=[user_email],
        fail_silently=False,
    )
