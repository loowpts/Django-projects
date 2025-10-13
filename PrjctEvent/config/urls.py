from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('apps.users.urls', namespace='users')),
    path('events/', include('apps.events.urls', namespace='events')),
    # path('tickets/', include('apps.tickets.urls', namespace='tickets')),
    # path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    # path('chat/', include('apps.chat.urls', namespace='chat')),
    # path('analytics/', include('apps.analytics.urls', namespace='analytics')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)