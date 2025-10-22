from django.urls import path
from .views import OrganizerDashboard


app_name = 'analytics'

urlpatterns = [
    path('dashboard/', OrganizerDashboard.as_view(), name='dashboard')
]

