from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.core.exceptions import PermissionDenied

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

        if not self.request.user.is_staff():
            qs = qs.filter(
                Q(status=Event.Status.PUBLISHED) | Q(status=Event.Status.DRAFT, author=self.request.user)
            )

        query = (self.request.GET.get('q') or '').strip()
        category = (self.request.GET.get('category') or '').strip()
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

        return ctx

class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'
    slug_fields = 'slug'
    slug_url_kwarg = 'slug'

    def get_object(self, queryset=None):
        event = super().get_object(queryset)
        if event.status == Event.Status.DRAFT and event.author != self.request.user and not self.request.user.is_staff:
            self.raise_exception = True
            self.handle_no_permission()
        Event.objects.filter(pk=event.pk).update(views_count=event.views_count + 1)
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
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.event = self.object
            review.user = self.request.user
            review.save()
            messages.success(request, 'Ваш отзыв отправлен на модерацию.')
            return redirect(self.get_success_url())
        else:
            messages.error(request, 'Ошибка в форме отзыва.')
            ctx = self.get_context_data()
            return self.render_to_response(ctx)

    def get_success_url(self):
        return reverse('events:event_detail', kwargs={'slug': self.object.slug})


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

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
        messages.error(self.request, 'У вас нету доступа для редактирования.')
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
        messages.error(self.request, 'У вас нету доступа для удаления.')

    def get_success_url(self):
        messages.success(self.request, 'Событие удалено.')
        return self.success_url


class EventArchiveView(LoginRequiredMixin, UserPassesTestMixin, ArchiveView):
    model = Event
    template_name = 'events/event_archive.html'
    context_object_name = 'events'
    paginate_by = 10

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
            qs = qs.filter(start_datetime_month=int(month))

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
        try:
            review = form.save()
        except IntegrityError:
            form.add_error(None, 'Не удалось добавить отзыв: возможен дубликат. Если вы уже оставляли отзыв, его можно отредактировать.')
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
        kwargs['request'] = self.request
        return kwargs

    def test_func(self):
        review = super().get_object()
        return self.request.user.is_staff or review.author == self.request.user

    def handle_no_permission(self):
        messages.error(self.request, 'Вы не можете редактировать этот отзыв.')
        return super().handle_no_permission()

    def form_valid(self, form):
        messages.success(self.request, 'Отзыв успешно обновлен.')
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.event.get_absolute_url()

class ReviwDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Review
    template_name = 'events/reviw_confirm_delete.html'

    def test_func(self):
        review = super().get_object()
        return self.request.user.is_staff or event.author == self.request.user

    def handle_no_permission(self):
        messages.success(self.request, 'У вас нету прав на удаления.')
        return super().handle_no_permission()

    def get_success_url(self):
        return self.object.event.get_absolute_url()


class ReviwListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Review
    template_name = 'events/reviw_list.html'
    context_object_name = 'reviews'
    paginate_by = 20

    def test_func(self):
        review = super().get_object()
        return self.request.user.is_staff

    def get_queryset(self):
        qs = Review.objects.select_related('author', 'category').prefetch_related('tags')
        query = self.request.GET.get('query', '').strip()

        if query:
            qs = qs.filter(
                models.Q(event__title__icontains=query) |
                models.Q(user__email__icontains=query) |
                models.Q(user__first_name__icontains=query) |
                models.Q(user__last_name__icontains=query)
            )
        approved = (self.request.GET.get('approved'))
        if approved in ('0', '1'):
            qs = qs.filter(approved(approved == '1'))
        return qs
