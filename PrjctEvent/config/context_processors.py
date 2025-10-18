from apps.notifications.models import Notification

def notifications(request):
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
    else:
        unread_notifications = 0
    return {'unread_notifications': unread_notifications}
