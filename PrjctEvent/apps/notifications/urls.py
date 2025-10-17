from django.urls import path
from .views import NotificationList, NotificationMarkReadView, NotificationMarkAllReadView

app_name = 'notifications'

urlpatterns = [
    path('', NotificationList.as_view(), name='notification_list'),
    path('read/<int:pk>/', NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('read/all/', NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
]
