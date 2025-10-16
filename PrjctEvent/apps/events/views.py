from typing import Any
from django.views.generic import TemplateView, DetailView, ListView
from django.views import View
from django.template.response import TemplateResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q, Avg
from django.utils.text import slugify
from django.db import transaction
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone

from .forms import EventForm, ReviewForm, EventArchiveForm, EventSearchForm
from .models import Event, Review, Category


def htmx_redirect(request, url):
    if request.headers.get('HX-Request'):
        response = HttpResponse(status=204)
        response['HX-Redirect'] = url
        return response
    return redirect(url)

class HTMXMixin:
    partial_template = None
    full_template = None
    
    def render_response(self, context):
        template = self.partial_template if self.request.headers.get('HX-Request') else self.full_template
        return TemplateResponse(self.request, template, context)

class EventList(HTMXMixin, ListView):
    partial_template = 'events/partials/event_list.html'
    full_template = 'events/event_list.html'
    paginate_by = 10
    context_object_name = 'events'

    def get_queryset(self):
        now = timezone.now()
        
        if self.request.user.is_authenticated:
            qs = Event.objects.filter(
                Q(author=self.request.user) | 
                (Q(status='PUBLISHED') & Q(start_datetime__gte=now))
            ).order_by('start_datetime')
        else:
            qs = Event.objects.filter(
                status='PUBLISHED',
                start_datetime__gte=now
            ).order_by('start_datetime')
        
        query = (self.request.GET.get('q') or '').strip()
        category_slug = self.kwargs.get('category_slug')
        status_filter = self.request.GET.get('status')

        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            qs = qs.filter(category=category)
            self.current_category = category
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(description__icontains=query))
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all()
        ctx['search_form'] = EventSearchForm(self.request.GET or None)
        ctx['search_query'] = self.request.GET.get('q')
        ctx['no_events'] = not self.get_queryset().exists()
        
        if hasattr(self, 'current_category'):
            ctx['current_category'] = self.current_category
        
        return ctx

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return self.render_response(context)


class EventDetail(HTMXMixin, DetailView):
    model = Event
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    partial_template = 'events/partials/event_detail.html'
    full_template = 'events/event_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.get_object()
        ctx['reviews'] = event.reviews.filter(approved=True)
        ctx['tickets'] = event.tickets.all() if hasattr(event, 'tickets') else []
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_response(context)


class EventCreate(LoginRequiredMixin, HTMXMixin, TemplateView):
    partial_template = 'events/partials/event_form.html'
    full_template = 'events/event_create.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = EventForm(request=self.request)
        return ctx

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_response(context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = EventForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            event = form.save(commit=False)
            event.author = request.user
            event.status = Event.Status.DRAFT
            if not event.slug:
                event.slug = slugify(event.title)
            event.save()
            form.save_m2m()

            return htmx_redirect(request, reverse('events:event_detail', kwargs={'slug': event.slug}))

        ctx = {'form': form}
        return self.render_response(ctx)


class EventUpdate(LoginRequiredMixin, UserPassesTestMixin, HTMXMixin, TemplateView):
    partial_template = 'events/partials/event_form.html'
    full_template = 'events/event_update.html'

    def test_func(self):
        event = self.get_object()
        return self.request.user == event.author or self.request.user.is_staff

    def get_object(self):
        return get_object_or_404(Event, slug=self.kwargs['slug'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        instance = self.get_object()
        ctx['form'] = EventForm(instance=instance, request=self.request)
        ctx['event'] = instance
        return ctx

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_response(context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        form = EventForm(request.POST, request.FILES, instance=instance, request=request)
        if form.is_valid():
            event = form.save(commit=False)
            if form.cleaned_data['title'] != instance.title:
                event.slug = slugify(event.title)
            event.save()
            form.save_m2m()

            return htmx_redirect(request, reverse('events:event_detail', kwargs={'slug': event.slug}))

        ctx = {'form': form, 'event': instance}
        return self.render_response(ctx)


class EventDelete(LoginRequiredMixin, UserPassesTestMixin, HTMXMixin, TemplateView):
    partial_template = 'events/partials/event_delete_confirm.html'
    full_template = 'events/event_delete.html'

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
        context = self.get_context_data(**kwargs)
        return self.render_response(context)

    def post(self, request, *args, **kwargs):
        event = self.get_object()
        event.delete()
        return htmx_redirect(request, reverse('events:event_list'))


class EventArchive(HTMXMixin, ListView):
    partial_template = 'events/partials/archive_list.html'
    full_template = 'events/archive.html'
    paginate_by = 10
    context_object_name = 'events'

    def get_queryset(self):
        now = timezone.now()
        qs = Event.objects.filter(
            status='PUBLISHED',
            start_datetime__lt=now
        ).order_by('-start_datetime')

        year = self.request.GET.get('year')
        month = self.request.GET.get('month')
        if year:
            qs = qs.filter(start_datetime__year=year)
        if month:
            qs = qs.filter(start_datetime__month=month)
        
        self.selected_year = year
        self.selected_month = month
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['selected_year'] = self.selected_year
        ctx['selected_month'] = self.selected_month
        return ctx

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return self.render_response(context)


class ReviewCreate(LoginRequiredMixin, HTMXMixin, TemplateView):
    partial_template = 'events/partials/review_form.html'
    full_template = 'events/review_create.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ReviewForm()
        ctx['event'] = get_object_or_404(Event, slug=self.kwargs['event_slug'])
        return ctx

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_response(context)

    def post(self, request, *args, **kwargs):
        event = get_object_or_404(Event, slug=self.kwargs['event_slug'])
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.event = event
            review.user = request.user
            review.approved = False
            review.save()

            return htmx_redirect(request, reverse('events:event_detail', kwargs={'slug': event.slug}))

        ctx = {'form': form, 'event': event}
        return self.render_response(ctx)


class ReviewUpdate(LoginRequiredMixin, UserPassesTestMixin, HTMXMixin, TemplateView):
    partial_template = 'events/partials/review_form.html'
    full_template = 'events/review_update.html'

    def test_func(self):
        review = self.get_object()
        return self.request.user == review.user or self.request.user.is_staff

    def get_object(self):
        return get_object_or_404(Review, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        instance = self.get_object()
        ctx['form'] = ReviewForm(instance=instance)
        ctx['review'] = instance
        return ctx

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_response(context)

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        form = ReviewForm(request.POST, instance=instance)
        if form.is_valid():
            review = form.save()
            return htmx_redirect(request, reverse('events:event_detail', kwargs={'slug': review.event.slug}))
        
        ctx = {'form': form, 'review': instance}
        return self.render_response(ctx)


class ReviewDelete(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        review = self.get_object()
        return self.request.user == review.user or self.request.user.is_staff

    def get_object(self):
        return get_object_or_404(Review, pk=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        event_slug = review.event.slug
        review.delete()
        return htmx_redirect(request, reverse('events:event_detail', kwargs={'slug': event_slug}))


class ReviewList(LoginRequiredMixin, UserPassesTestMixin, HTMXMixin, ListView):
    partial_template = 'events/partials/review_list.html'
    full_template = 'events/review_list.html'
    paginate_by = 10
    context_object_name = 'reviews'

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        qs = Review.objects.all().order_by('-created_at')

        approved = self.request.GET.get('approved')
        event_id = self.request.GET.get('event')
        if approved is not None:
            qs = qs.filter(approved=approved)
        if event_id:
            qs = qs.filter(event_id=event_id)
        
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return self.render_response(context)


class ApproveReviewView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)
        review.approved = True
        review.save()

        ctx = {'review': review, 'message': 'Approved'}
        return TemplateResponse(request, 'events/partials/review_row.html', ctx)


class RejectReviewView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)
        review.approved = False
        review.save()
        ctx = {'review': review, 'message': 'Rejected'}
        return TemplateResponse(request, 'events/partials/review_row.html', ctx)
