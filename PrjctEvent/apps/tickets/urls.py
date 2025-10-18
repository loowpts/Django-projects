from django.urls import path
from .views import (
    PurchaseView,
    RegisterView,
    UserTickets,
    SuccessView,
    CancelView,
    stripe_webhook
)

app_name = 'tickets'

urlpatterns = [
    path('<slug:event_slug>/purchase/', PurchaseView.as_view(), name='purchase'),
    path('<slug:event_slug>/register/', RegisterView.as_view(), name='register'),
    path('my-tickets/', UserTickets.as_view(), name='my_tickets'),
    path('success/<int:registration_id>/', SuccessView.as_view(), name='success'),
    path('cancel/<int:registration_id>/', CancelView.as_view(), name='cancel'),
    path('webhook/stripe/', stripe_webhook, name='stripe_webhook'),
]
