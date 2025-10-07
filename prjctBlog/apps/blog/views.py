from django.db.models.query import QuerySet
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView, CreateView, FormView, DeleteView
from .models import Category, Post, Comment, Like, Subscription
from .forms import PostForm, CategoryForm, CommentForm, LikeForm
from django.db.models import Q, F
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.urls import reverse, reverse_lazy
from django.template.response import TemplateResponse
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib import messages
from taggit.models import Tag
from django.utils import timezone
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


class LikeCreateView(LoginRequiredMixin, CreateView):
    def post(self, request, *args, **kwargs):
        post_slug = kwargs.get('post_slug')
        comment_id = kwargs.get('comment_id')
        value = int(request.POST.get('value', 1)) # Для 1 лайка или 1 дизлайка

        if post_slug:
            obj = get_object_or_404(Post, slug=post_slug)
            obj_type = 'post'
        elif comment_id:
            obj = get_object_or_404(Comment, id=comment_id)
            obj_type = 'comment'
        else:
            return JsonResponse({'error': 'Object not specified'}, status=400)
        
        #Проверка на существующий лайк
        like_kwargs = {'user': request.user}
        if obj_type == 'post':
            like_kwargs['post'] = obj
        else:
            like_kwargs['comment'] = obj

        like, created = Like.objects.get_or_create(**like_kwargs, defaults={'value': value})
        if not created:
            if like.value == value:
                like.delete() # Если тот же value, удаляем(toggle off)
                new_count = self.get_like_count(obj, obj_type)
                return JsonResponse({
                    'success': True,
                    'count': new_count,
                    'action': 'removed'
                })
            else:
                like.value = value # Меняем value
                like.save()
        new_count = self.get_like_count(obj, obj_type)
        return JsonResponse({
            'success': True,
            'count': new_count,
            'action': 'updated'
        })
    
    def get_like_count(self, obj, obj_type):
        if obj_type == 'post':
            return Like.objects.filter(post=obj).aggregate(total=models.Sum('value'))['total'] or 0
        else:
            return Like.objects.filter(comment=obj).aggregate(total=models.Sum('value'))['total'] or 0


class LikeDeleteView(LoginRequiredMixin, DeleteView):
    def post(self, request, *args, **kwargs):
        post_slug = kwargs.get('post_slug')
        comment_id = kwargs.get('comment_id')

        if post_slug:
            obj = get_object_or_404(Post, slug=post_slug)
            obj_type = 'post'
            like = get_object_or_404(Like, user=request.user, post=obj)
        elif comment_id:
            obj = get_object_or_404(Comment, slug=comment_id)
            obj_type = 'comment'
            like = get_object_or_404(Like, user=request.user, comment=obj)
        else:
            return JsonResponse({
                'error': 'Object not specified'
            }, status=400)
        
        like.delete()
        new_count = self.get_like_count(obj, obj_type)
        return JsonResponse({
            'success': True,
            'count': new_count,
            'action': 'deleted'
        })
    
    def get_like_count(self, obj, obj_type):
        if obj_type:
            return Like.objects.filter(post=obj).aggregate(total=models.Sum('value'))['total'] or 0
        else:
            return Like.objects.filter(comment=obj).aggregate(total=models.Sum('value'))['total'] or 0


class SubscriptionListView(LoginRequiredMixin, ListView):
    model = Subscription
    template_name = 'blog/subscription_list.html'
    context_object_name = 'subscriptions'

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user).select_related('category')
    
    
class SubscriptionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        category_slug = kwargs.get('category_slug')
        category = get_object_or_404(Category, slug=category_slug)

        subscription, created = Subscription.objects.get_or_create(
            user=request.user,
            category=category
        )
        if created:
            messages.success(request, 'Вы успешно подписались на категорию.')
            count = category.subscriptions.count() # Подсчёт подписчиков
            return JsonResponse({
                'success': True,
                'action': 'subscribed',
                'count': count
            })
        else:
            return JsonResponse({'error': 'Вы уже подписаны'}, status=400)


class SubscriptionDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        category_slug = kwargs.get('categoru_slug')
        category = get_object_or_404(Category, slug=category_slug)
        subscription = get_object_or_404(Subscription, user=request.user, category=category)
        subscription.delete()
        messages.success(request, 'Вы отписались от категории.')
        count = category.subscriptions.count()
        return JsonResponse({
            'success': True,
            'action': 'unsubscribed',
            'count': count
        })


