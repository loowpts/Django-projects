from celery import shared_task
from django.core.mail import send_mail
from .models import Notification

@shared_task
def send_notification_email(notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=None,
            recipient_list=[notification.user.email],
            fail_silently=False,
        )
        print(f'Email sent for notification {notification_id}')
    except Notification.DoesNotExist as e:
        print(f'Error in task: {e}')
