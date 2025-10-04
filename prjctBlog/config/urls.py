from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('blog/', include('apps.blog.urls', namespace='blog' )),
    path('users/', include('apps.users.urls', namespace='users' )),
]
