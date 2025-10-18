from django.template.response import TemplateResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import NotificationFilterForm
from .models import Notification

class NotificationList(LoginRequiredMixin, ListView):
    template_name = 'notifications/notification_list.html'
    partial_template = 'notifications/partials/notification_list.html'
    paginate_by = 10
    context_object_name = 'page_obj'

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user).order_by('-created_at')
        filter_form = NotificationFilterForm(self.request.GET or None)
        if filter_form.is_valid():
            if filter_form.cleaned_data.get('is_read'):
                is_read_bool = filter_form.cleaned_data['is_read'] == 'true'
                qs = qs.filter(is_read=is_read_bool)
            if filter_form.cleaned_data.get('notification_type'):
                qs = qs.filter(notification_type=filter_form.cleaned_data['notification_type'])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = NotificationFilterForm(self.request.GET or None)
        context['page_title'] = 'Уведомления'
        return context

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, self.partial_template, context)
        context['include_partial'] = self.partial_template
        return TemplateResponse(request, self.template_name, context)
    

class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.mark_as_read()
        
        message.success(request, 'Уведомление помечено как прочитанное.')
        if request.headers.get('HX-Request'):
            response = TemplateResponse(request, 'notifications/partials/notification_row.html')
            response['HX-Redirect'] = reverse('notifications:notification_list')
            return response
        return htmx_redirect(request, reverse('notifications:notification_list'))
    
class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

        message.success(request, 'Все уведомления помечены как прочитанные.')
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('notifications:notification_list')
            return response
        return htmx_redirect(request, reverse('notifications:notification_list'))
