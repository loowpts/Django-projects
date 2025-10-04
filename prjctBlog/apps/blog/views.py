from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView, CreateView, FormView, DeleteView
from .models import Category, Post, Comment
from .forms import PostForm, CategoryForm, CommentForm
from django.db.models import Q, F
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.urls import reverse, reverse_lazy
from django.template.response import TemplateResponse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.contrib import messages
from taggit.models import Tag
from django.core.exceptions import PermissionDenied


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 15

    def get_queryset(self):
        qs = (
            Post.objects.filter(status='published')
            .select_related('author', 'category')
            .prefetch_related('tags')
            .order_by('-published_at')
        )

        q = (self.request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))

        category_slug = (self.kwargs.get('category_slug') or self.request.GET.get('category'))
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        tag_slug = (self.kwargs.get('tag_slug') or self.request.GET.get('tag'))
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get('q') or '').strip()
        category_slug = (self.kwargs.get('category_slug') or self.request.GET.get('category'))
        tag_slug = (self.kwargs.get('tag_slug') or self.request.GET.get('tag'))

        ctx['category_slug'] = category_slug
        ctx['tag_slug'] = tag_slug

        if category_slug:
            ctx['current_category'] = get_object_or_404(Category, slug=category_slug)
        if tag_slug:
            ctx['current_tag'] = get_object_or_404(Tag, slug=tag_slug)

        ctx['query_string'] = self.request.META.get('QUERY_STRING', '')
        return ctx


class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_object(self):
        obj = super().get_object()

        draft_value = getattr(Post.status, 'DRAFT', 'draft')

        if getattr(obj, 'status', None) == draft_value and obj.author != self.request.user:
            raise Http404('Этот пост не доступен')
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["comments"] = self.object.comments.filter(is_public=True)
        return ctx


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user

        self.object = form.save(commit=False)
        self.object = form.save()

        if hasattr(form, 'save_m2m'):
            form.save_m2m()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        return reverse_lazy('blog:post_detail', kwargs={'slug': self.object.slug})


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'

    def test_func(self):
        post = self.get_object()
        return post.author == self.request.user or self.request.user.is_staff

    def form_valid(self, form):
        post_obj = form.save(commit=False)

        if post_obj.author != self.request.user and self.request.user.is_staff:
            raise PermissionDenied('У вас нету прав на редактирования поста.')

        post_obj.save()
        if hasattr(form, 'save_m2m'):
            form.save_m2m()

        self.object = post_obj

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        return reverse_lazy('blog:post_detail', kwargs={'slug': self.object.slug})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/post_confirm_delete.html'
    success_url = reverse_lazy('blog_post_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        post = super().get_object()
        if post.author != self.request.user and not self.request.user.is_staff:
            raise Http404('Вы не можете удалить эту задачу.')
        return post


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.post_obj = get_object_or_404(Post, slug=kwargs.get('slug'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['post'] = self.post_obj

        parent_id = self.request.GET.get('parent_id')
        if parent_id:
            try:
                parent_pk = int(parent_id)
            except (TypeError, ValueError):
                parent_pk = None

            if parent_pk:
                ctx['parent'] = get_object_or_404(Comment, id=parent_pk, post=self.post_obj)
        return ctx

    def form_valid(self, form):
        form.instance.post = self.post_obj
        form.instance.author = self.request.user

        parent_id = self.request.GET.get('parent_id')
        if parent_id:
            try:
                parent_pk = int(parent_id)
            except (TypeError, ValueError):
                parent_pk = None

            if parent_pk:
                form.instance.parent = get_object_or_404(Comment, id=parent_pk, post=self.post_obj)

        self.object = form.save()
        messages.success(self.request, 'Комментарий добавлен.')
        return redirect(self.get_success_url())

    def get_success_url(self) -> str:
        return reverse('blog:post_detail', kwargs={'slug': self.object.post.slug})


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment_form.html'

    def get_object(self):
        comment = super().get_object()
        if comment.author != self.request.user and not self.request.user.is_staff:
            raise Http404('Вы не можете редактировать этот комментарий.')
        return comment

    def form_valid(self, form):
        comment_obj = form.save(commit=False)

        if comment_obj.author != self.request.user and self.request.user.is_staff:
            raise PermissionDenied('У вас нету прав на редактирования.')

        comment_obj.save()
        if hasattr(form, 'save_m2m'):
            form.save_m2m()

        self.object = comment_obj

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        return reverse_lazy('blog:post_detail', kwargs={'slug': self.object.post.slug})


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment_confirm_delete.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(self.request, 'Войдите, чтобы удалить комментарий.')
            return redirect('users:login')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        comment = super().get_object()
        if comment.author != self.request.user and not self.request.user.is_staff:
            raise Http404('Вы не можете удалить этот комментарий.')
        return comment

    def get_success_url(self) -> str:
        return reverse_lazy('blog:post_detail', kwargs={'slug': self.object.post.slug})
