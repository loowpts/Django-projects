from django.db import models
from django.contrib.auth import get_user_model
from apps.events.models import Event

User = get_user_model()


class ChatMessage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f'{self.user.email}: {self.message[:50]}'    
