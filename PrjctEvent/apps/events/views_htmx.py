from typing import Any
from django.views.generic import TemplateView, DetailView
from django.views import View
from django.template.response import TemplateResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q
from django.utils.text import slugify
from django.db import transaction

from .forms import EventForm, ReviewForm, EventArchiveForm, SearchForm
from .models import Event, Review, Category


class EventList(TemplateView):
    template_name = 'events/base.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        events = Event.objects.filter(status='PUBLISHED').order_by('-start_datetime')
        categories = Category.objects.all()
        
        query = (self.request.GET.get('q') or '').strip()
        category_slug = kwargs.pop('category_slug')
        status_filter = self.request.GET.get('status')
        
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            events = events.filter(category=category)
            ctx['current_category'] = category
        if query:
            events = events.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )

        search_form = SearchForm()
        if search_form.is_valid():
            pass
        
        if status_filter:
            events = events.filter(status=status_filter)
        
        ctx['no_events'] =  not events.exists()
        
        ctx.update({
            'events': events,
            'categories': categories,
            'search_form': search_form,
            'search_query': query
        })
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/event_list_partial.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)


class EventDetailView(DetailView):
    model = Event
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    template_name = 'events/base.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.get_object()  # Handles 404
        ctx['reviews'] = event.reviews.filter(approved=True)
        ctx['tickets'] = event.tickets.all()
        return ctx
    
    def get(self, request, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/event_detail_partial.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)


class EventCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'events/base.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = EventForm(request=self.request)
        return ctx
    
    def get(self, request, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/event_form_partial.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = EventForm(request.POST, request=request)
        if form.is_valid():
            event = form.save(commit=False)
            event.author = request.user
            event.status = Event.Status.DRAFT
            if not event.slug:
                event.slug = slugify(event.title)
            event.save()
            if request.headers.get('HX-Request'):
                return TemplateResponse(request, 'events/partials/event_form_partial.html', {'event': event})
            return redirect('events:event_list')
        
        ctx = {'form': form}
        return TemplateResponse(request, 'events/partials/event_form_partial.html', ctx)


class EventUpdate(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'events/base.html'
    
    def test_func(self):
        event = self.get_object()
        return self.request == event.author or self.request.user.is_staff
    
    def get_object(self):
        return get_object_or_404(Event, slug=self.kwargs['slug'])
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        instance = self.get_object()
        ctx['form'] = EventForm(instance=instance, request=self.request)
        return ctx
    
    def get(self, request, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/event_form_partial.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        form = EventForm(request.POST, instance=instance, request=request)
        if form.is_valid():
            event = form.save(commit=False)
            if form.cleaned_data['title'] != instance.title:
                event.slug = slugify(event.title)
            event.save()
            if request.headers.get('HX-Request'):
                return TemplateResponse(request, 'events/partials/success_partial.html', {'event': event})
            return redirect('events:event_detail', slug=event.slug)
        
        ctx = {'form': form}
        return TemplateResponse(request, 'events/partials/event_form_partial.html', ctx)


class EventDelete(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'events/base.html'
    
    def test_func(self):
        event = self.get_object()
        return self.request.user == event.author or self.request.user.is_staff
    
    def get_object(self):
        return get_object_or_404(Event, slug=self.kwargs['slug'])
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['event'] = self.get_object()
        return ctx
    
    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/delete_confirm_partial.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)
    
    def post(self, request, *args, **kwargs):
        event = self.get_object()
        event.delete()
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/deleted_partial.html', {'message': 'Deleted'})
        return redirect('events:event_list')
    
class EventArchive(TemplateView):
    template_name = 'events/base.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        events = Event.objects.filter(status='PUBLISHED')
        
        year = self.request.GET.get('year')
        month = self.request.GET.get('month')
        if year:
            events = events.filter(start_datetime__year=year)
        if month:
            events = events.filter(start_datetime__month=month)
        
        page = self.request.GET.get('page', 1)
        
        ctx.update({
            'events': events.order_by('-start_datetime'),
            'selected_year': year,
            'selected_month': month,
        })
        return ctx
    
    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/archive_list_partial.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)
            
        
        
class ApproveReviewView(UserPassesTestMixin, View):
    def test_func(self) -> bool | None:
        return self.request.user.is_staff
    
    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)
        review.approved = True
        review.save()
        
        ctx = {'review': review}
        return TemplateResponse(request, 'events/partials/review_row_partial.html', ctx)
