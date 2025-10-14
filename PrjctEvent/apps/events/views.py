from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q, F
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db import IntegrityError
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.generic import (
    ListView, DetailView,
    UpdateView, CreateView,
    DeleteView, View
)

from apps.users.models import UserProfile
from .models import Category, Event, Review, Tag
from .forms import EventForm, ReviewForm, SearchForm, EventArchiveForm


class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 10

    def get_queryset(self):
        qs = Event.objects.select_related('author', 'category').prefetch_related('tags')

        if not self.request.user.is_staff:
            qs = qs.filter(
                Q(status=Event.Status.PUBLISHED) | Q(status=Event.Status.DRAFT, author=self.request.user)
            )

        query = (self.request.GET.get('q') or '').strip()
        category_slug = (self.request.GET.get('category') or '').strip()
        status = (self.request.GET.get('status') or '').strip()

        if query:
            qs = qs.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )
        if category_slug and Category.objects.filter(slug=category_slug).exists():
            qs = qs.filter(category__slug=category_slug)

        if status in Event.Status.values:
            qs = qs.filter(status=status)

        return qs.order_by('-start_datetime')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = SearchForm(self.request.GET)
        ctx['query'] = self.request.GET.get('q', '')
        ctx['category_slug'] = self.request.GET.get('category', '')
        ctx['status'] = self.request.GET.get('status', '')
        ctx['categories'] = Category.objects.all()
        ctx['statuses'] = Event.Status.choices
        category_slug = self.request.GET.get('category', '').strip()
        if category_slug:
            category = Category.objects.filter(slug=category_slug).first()
            ctx['category_name'] = category.name if category else 'Без категории'
        else:
            ctx['category_name'] = ''
        return ctx


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_object(self, queryset=None):
        event = super().get_object(queryset)
        if event.status == Event.Status.DRAFT and event.author != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied()

        Event.objects.filter(pk=event.pk).update(views_count=F('views_count') + 1)
        event.refresh_from_db()
        return event

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['reviews'] = self.object.reviews.filter(
            Q(approved=True) | Q(user=self.request.user)
        ).select_related('user')
        ctx['review_form'] = ReviewForm()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = ReviewForm(request.POST, request=request)
        if form.is_valid():
            review = form.save(commit=False)
            review.event = self.object
            review.user = self.request.user
            review.approved = False
            review.save()
            messages.success(request, 'Ваш отзыв отправлен на модерацию.')
            return redirect(self.get_success_url())
        else:
            messages.error(request, 'Ошибка в форме отзыва.')
            ctx = self.get_context_data()
            ctx['review_form'] = form
            return self.render_to_response(ctx)

    def get_success_url(self):
        return reverse('events:event_detail', kwargs={'slug': self.object.slug})


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:event_list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.status = Event.Status.DRAFT
        if hasattr(self.request.user, 'userprofile'):
            self.request.user.userprofile.role = UserProfile.Role.ORGANIZER
            self.request.user.userprofile.save()
        messages.success(self.request, 'Событие успешно создано.')
        return super().form_valid(form)

class EventUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:event_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def test_func(self):
        event = super().get_object()
        return self.request.user.is_staff or event.author == self.request.user

    def handle_no_permission(self):
        messages.error(self.request, 'У вас нет доступа для редактирования.')
        return super().handle_no_permission()

    def form_valid(self, form):
        messages.success(self.request, 'Событие успешно обновлено.')
        return super().form_valid(form)


class EventDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Event
    template_name = 'events/event_confirm_delete.html'
    success_url = reverse_lazy('events:event_list')

    def test_func(self):
        event = super().get_object()
        return self.request.user.is_staff or event.author == self.request.user

    def handle_no_permission(self):
        messages.error(self.request, 'У вас нет доступа для удаления.')
        return super().handle_no_permission()

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Событие успешно удалено.')
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return self.success_url


class EventArchiveView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Event
    template_name = 'events/event_archive.html'
    context_object_name = 'events'
    paginate_by = 10

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        qs = Event.objects.select_related('author', 'category').prefetch_related('tags')

        if not self.request.user.is_staff:
            qs = qs.filter(
                Q(status=Event.Status.PUBLISHED) | Q(status=Event.Status.DRAFT, author=self.request.user)
            )
        year = self.request.GET.get('year', '').strip()
        month = self.request.GET.get('month', '').strip()

        if year and year.isdigit():
            qs = qs.filter(start_datetime__year=int(year))
        if month and month.isdigit():
            qs = qs.filter(start_datetime__month=int(month))

        return qs.order_by('-start_datetime')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = EventArchiveForm(self.request.GET)
        ctx['year'] = self.request.GET.get('year', '').strip()
        ctx['month'] = self.request.GET.get('month', '').strip()
        ctx['years'] = Event.objects.filter(
            Q(status=Event.Status.PUBLISHED) | Q(status=Event.Status.DRAFT, author=self.request.user)
        ).dates('start_datetime', 'year', order='DESC')
        return ctx


class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = 'events/review_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, slug=self.kwargs['slug'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
            'event': self.event,
        })
        return kwargs

    def form_valid(self, form):
        review = form.save(commit=False)
        review.user = self.request.user
        review.event = self.event
        review.approved = False
        try:
            review.save()
        except IntegrityError:
            form.add_error(None, 'Вы уже оставили отзыв для этого события.')
            return self.form_invalid(form)

        messages.success(self.request, 'Спасибо! Ваш отзыв добавлен и ожидает модерации.')
        return  redirect(self.event.get_absolute_url())

    def form_invalid(self, form):
        messages.error(self.request, 'Пожалуйста, исправьте ошибки в форме.')
        return super().form_invalid(form)


class ReviewUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Review
    form_class = ReviewForm
    template_name = 'events/review_form.html'
    context_object_name = 'review'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def test_func(self):
        review = super().get_object()
        return self.request.user.is_staff or review.user == self.request.user

    def handle_no_permission(self):
        messages.error(self.request, 'Вы не можете редактировать этот отзыв.')
        return super().handle_no_permission()

    def form_valid(self, form):
        messages.success(self.request, 'Отзыв успешно обновлен.')
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.event.get_absolute_url()

class ReviewDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Review
    template_name = 'events/review_confirm_delete.html'

    def test_func(self):
        review = super().get_object()
        return self.request.user.is_staff or review.user == self.request.user

    def handle_no_permission(self):
        messages.success(self.request, 'У вас нет прав на удаления.')
        return super().handle_no_permission()

    def get_success_url(self):
        return self.object.event.get_absolute_url()


class ReviewListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Review
    template_name = 'events/review_list.html'
    context_object_name = 'reviews'
    paginate_by = 20

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        qs = Review.objects.select_related('user', 'event')
        query = self.request.GET.get('query', '').strip()

        if query:
            qs = qs.filter(
                Q(event__title__icontains=query) |
                Q(user__email__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query)
            )
        approved = self.request.GET.get('approved', '')
        if approved in ('0', '1'):
            qs = qs.filter(approved=(approved == '1'))
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['query'] = self.request.GET.get('query', '').strip()
        ctx['approved'] = self.request.GET.get('approved', '')
        return ctx

class ApproveReviewView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, 'У вас нет прав для этой операции.')
        return super().handle_no_permission()

    @method_decorator(require_POST)
    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)
        if review.approved:
            messages.info(request, 'Отзыв уже одобрен.')
        else:
            review.approved = True
            review.save(update_fields=['approved'])
            messages.success(request, 'Отзыв успешно одобрен.')
        return redirect(request.META.get('HTTP_REFERER') or reverse_lazy('events:review_list'))


class RejectReviewView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, 'У вас нет прав для операции.')
        return super().handle_no_permission()

    @method_decorator(require_POST)
    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)

        if not review.approved:
            messages.info(request, 'Отзыв уже отмечен как не одобренный.')
        else:
            review.approved = False
            review.save(update_fields=['approved'])
            messages.success(request, 'Отзыв помечен как не одобренный.')
        return redirect(request.META.get('HTTP_REFERER') or reverse_lazy('events:review_list'))
