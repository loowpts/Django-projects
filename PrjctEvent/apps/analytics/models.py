from django.db import models
from django.contrib.auth import get_user_model
from apps.events.models import Event
from apps.notifications.models import Notification

User = get_user_model()

class AnalyticsMetric(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_count = models.IntegerField(default=0)
    ticket_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_rating = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Метрика аналитики'
        verbose_name_plural = 'Метрики аналитики'
        
    
        
