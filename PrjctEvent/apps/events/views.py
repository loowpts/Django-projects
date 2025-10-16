from typing import Any
from django.views.generic import TemplateView, DetailView
from django.views import View
from django.template.response import TemplateResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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

        events_qs = Event.objects.filter(status='PUBLISHED').order_by('-start_datetime')
        categories = Category.objects.all()

        query = (self.request.GET.get('q') or '').strip()
        category_slug = self.kwargs.get('category_slug')
        status_filter = self.request.GET.get('status')

        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            events_qs = events_qs.filter(category=category)
            ctx['current_category'] = category
        if query:
            events_qs = events_qs.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )

        search_form = SearchForm(self.request.GET or None)
        if self.request.GET:
            search_form.is_valid()

        if status_filter:
            events_qs = events_qs.filter(status=status_filter)

        # Пагинация
        paginator = Paginator(events_qs, 10)
        page = self.request.GET.get('page')
        try:
            events = paginator.page(page)
        except PageNotAnInteger:
            events = paginator.page(1)
        except EmptyPage:
            events = paginator.page(paginator.num_pages)

        ctx['no_events'] = not events_qs.exists()
        ctx.update({
            'events': events,
            'categories': categories,
            'search_form': search_form,
            'search_query': query,
            'is_paginated': events.has_other_pages(),
        })
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/event_list.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)


class EventDetail(DetailView):
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
            return TemplateResponse(request, 'events/partials/event_detail.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)


class EventCreate(LoginRequiredMixin, TemplateView):
    template_name = 'events/base.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = EventForm(request=self.request)
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/event_form.html', ctx)
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
                return TemplateResponse(request, 'events/partials/event_form.html', {'event': event})
            return redirect('events:event_list')

        ctx = {'form': form}
        return TemplateResponse(request, 'events/partials/event_form.html', ctx)


class EventUpdate(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'events/base.html'

    def test_func(self):
        event = self.get_object()
        return self.request.user == event.author or self.request.user.is_staff

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
            return TemplateResponse(request, 'events/partials/event_form.html', ctx)
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
                return TemplateResponse(request, 'events/partials/event_success_partial.html', {'event': event})
            return redirect('events:event_detail', slug=event.slug)

        ctx = {'form': form}
        return TemplateResponse(request, 'events/partials/event_form.html', ctx)


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
            return TemplateResponse(request, 'events/partials/event_delete_confirm.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        event = self.get_object()
        event.delete()
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/event_deleted.html', {'message': 'Deleted'})
        return redirect('events:event_list')


class EventArchive(TemplateView):
    template_name = 'events/base.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        events_qs = Event.objects.filter(status='PUBLISHED')

        year = self.request.GET.get('year')
        month = self.request.GET.get('month')
        if year:
            events_qs = events_qs.filter(start_datetime__year=year)
        if month:
            events_qs = events_qs.filter(start_datetime__month=month)

        paginator = Paginator(events_qs.order_by('-start_datetime'), 10)
        page = self.request.GET.get('page')
        try:
            events = paginator.page(page)
        except PageNotAnInteger:
            events = paginator.page(1)
        except EmptyPage:
            events = paginator.page(paginator.num_pages)

        ctx.update({
            'events': events,
            'selected_year': year,
            'selected_month': month,
            'is_paginated': events.has_other_pages(),
        })
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/archive_list.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)


class ReviewCreate(LoginRequiredMixin, TemplateView):
    template_name = 'events/base.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ReviewForm(request=self.request)
        ctx['event'] = get_object_or_404(Event, slug=kwargs['event_slug'])
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/review_form.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        event = get_object_or_404(Event, slug=kwargs['event_slug'])
        form = ReviewForm(request.POST, request=request)
        if form.is_valid():
            review = form.save(commit=False)
            review.event = event
            review.user = request.user
            review.approved = False
            review.save()
            if request.headers.get('HX-Request'):
                return TemplateResponse(request, 'events/partials/review_added.html', {'review': review})
            return redirect('events:event_detail', slug=event.slug)
        ctx = {'form': form, 'event': event}
        return TemplateResponse(request, 'events/partials/review_form.html', ctx)


class ReviewUpdate(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'events/base.html'

    def test_func(self):
        review = self.get_object()
        return self.request.user == review.user or self.request.user.is_staff

    def get_object(self):
        return get_object_or_404(Review, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        instance = self.get_object()
        ctx['form'] = ReviewForm(instance=instance, request=self.request)
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/review_form.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        form = ReviewForm(request.POST, instance=instance, request=request)
        if form.is_valid():
            review = form.save()
            if request.headers.get('HX-Request'):
                return TemplateResponse(request, 'events/partials/review_updated.html', {'review': review})
            return redirect('events:review_list')
        ctx = {'form': form}
        return TemplateResponse(request, 'events/partials/review_form.html', ctx)


class ReviewDelete(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        review = self.get_object()
        return self.request.user == review.user or self.request.user.is_staff

    def get_object(self):
        return get_object_or_404(Review, pk=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        review.delete()
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/review_deleted.html', {})
        return redirect('events:review_list')


class ReviewList(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'events/base.html'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reviews_qs = Review.objects.all().order_by('-created_at')

        approved = self.request.GET.get('approved')
        event_id = self.request.GET.get('event')
        if approved is not None:
            reviews_qs = reviews_qs.filter(approved=approved)
        if event_id:
            reviews_qs = reviews_qs.filter(event_id=event_id)

        # Пагинация
        paginator = Paginator(reviews_qs, 10)
        page = self.request.GET.get('page')
        try:
            reviews = paginator.page(page)
        except PageNotAnInteger:
            reviews = paginator.page(1)
        except EmptyPage:
            reviews = paginator.page(paginator.num_pages)

        ctx.update({'reviews': reviews, 'is_paginated': reviews.has_other_pages()})
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'events/partials/review_list.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)


class ApproveReviewView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)
        review.approved = True
        review.save()

        ctx = {'review': review, 'message': 'Approved'}
        return TemplateResponse(request, 'events/partials/review_row.html', ctx)


class RejectReview(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)
        review.approved = False
        review.save()
        ctx = {'review': review, 'message': 'Rejected'}
        return TemplateResponse(request, 'events/partials/review_row.html', ctx)
