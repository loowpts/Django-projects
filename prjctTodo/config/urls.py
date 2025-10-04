from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('todo/', include('apps.todo.urls', namespace='todo')),
    path('users/', include('apps.users.urls', namespace='users')),
]
