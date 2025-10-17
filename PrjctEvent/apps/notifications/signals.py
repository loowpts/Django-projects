from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Notification
from .tasks import send_notification_email

User = get_user_model()

@receiver(post_save, sender='events.Event')
def create_event_notification(sender, instance, created, **kwargs):
    if created:
        admins = User.objects.filter(is_staff=True)
        for admin_user in admins:
            notification = Notification.objects.create(
                user=admin_user,
                title=f"Новое событие: {instance.title}",
                message=f"Создано событие '{instance.title}' пользователем {instance.author}.",
                event=instance,
                notification_type='EVENT'
            )
            send_notification_email.delay(notification.id)

@receiver(post_save, sender='events.Review')
def create_review_notification(sender, instance, created, **kwargs):
    if created:
        notification = Notification.objects.create(
            user=instance.event.author,
            title=f"Новый отзыв к '{instance.event.title}'",
            message=f"Пользователь {instance.user} оставил отзыв: {instance.text[:50]}...",
            review=instance,
            notification_type='REVIEW'
        )
        send_notification_email.delay(notification.id)
