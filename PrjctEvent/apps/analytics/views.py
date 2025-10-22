from typing import Any
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from collections import defaultdict
from datetime import timedelta
from .models import AnalyticsMetric
from apps.events.models import Event
from apps.users.models import User
from apps.tickets.models import Ticket
from apps.notifications.models import Notification


class OrganizerDashboard(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/dashboard.html'
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.profile.role != 'organizer' and not user.is_staff:
            return ctx
        
        now = timezone.now()
        month_ago = now - timedelta(days=30)
        
        events_data = Event.objects.filter(
            author=user,
            created_at__gte=month_ago
        ).extra({'month': "strftime('%%Y-%%m', created_at)"}).values('month').annotate(count=Count('id')).order_by('month')
        events_labels = [item['month'] for item in events_data]
        events_data_points = [item['count'] for item in events_data]
        ctx['events_chart'] = {
            'labels': events_labels,
            'data': events_data_points,
        }
        
        new_users = User.objects.filter(date_joined__gte=month_ago).count()
        total_users = User.objects.count()
        ctx['user_stats'] = {
            'new_users': new_users,
            'total_users': total_users,
        }
        
        tickets = Ticket.objects.filter(event__author=user)
        total_sales = tickets.aggregate(total=Sum('price'))['total'] or 0
        ctx['ticket_stats'] = {
            'total_sales': float(total_sales),
            'ticket_count': tickets.count(),
        }
        
        reviews_avg = tickets.aggregate(avg_rating=Avg('reviews__rating'))['avg_rating'] or 0
        ctx['review_stats'] = {'average_rating': reviews_avg or 0}
        
        notifications = Notification.objects.filter(user=user)
        sent = notifications.filter(is_sent=True).count()
        read = notifications.filter(is_read=True).count()
        ctx['notification_stats'] = {
            'sent': sent,
            'read': read,
            'unread': notifications.count() - read,
        }
        
        return ctx
