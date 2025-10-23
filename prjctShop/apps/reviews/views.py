from django.views.generic import TemplateView, ListView
from django.views import View
from django.template.response import TemplateResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse
from django.urls import reverse

from .forms import ReviewForm
from .models import Review
from apps.products.models import Product


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


class EventCreate(LoginRequiredMixin, HTMXMixin, TemplateView):
    partial_template = 'reviews/partials/review_form.html'
    template_name = 'reviews/review_create.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ReviewForm()
        ctx['product'] = get_object_or_404(Product, slug=self.kwargs['product_slug'])
        
    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        return self.render_response(ctx)
    
    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, slug=self.kwargs['product_slug'])
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.approved = False
            review.save()
            
            return htmx_redirect(request, reverse('events:event_detail', kwargs={'slug': product.slug}))
        
        ctx = {
            'form': form,
            'product': product
        }
        
        return self.render_response(ctx)
        

class ReviewUpdate(LoginRequiredMixin, UserPassesTestMixin, HTMXMixin, TemplateView):
    partial_template = 'reviews/partials/review_form'
    full_template = 'reviews/review_update.html'
    
    def test_func(self):
        review = self.get_object()
        return self.request.user == review.user or self.request.user.is_staff
    
    def get_object(self):
        return get_object_or_404(Review, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        instance = self.get_object()
        ctx['form'] = ReviewForm()
        ctx['review'] = instance
        return ctx
    
    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        return self.render_response(ctx)
    
    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        form = ReviewForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return htmx_redirect(request, reverse('products:product_detail', kwargs={'slug': review.product.slug}))
        
        ctx = {
            'form': form,
            'review': instance,
        }
        return self.render_response(ctx)


class ReviewDelete(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self) -> bool | None:
        review = self.get_object()
        return self.request.user == review.user or self.request.user.is_staff
    
    def get_object(self):
        return get_object_or_404(Review, pk=self.kwargs['pk'])
    
    def post(self, request, *args, **kwargs):
        review = self.get_object()
        product_slug = review.product.slug
        review.delete()
        return htmx_redirect(request, reverse('products:product_detail', kwargs={'slug': 'product_slug'}))
    

class ReviewList(LoginRequiredMixin, UserPassesTestMixin, HTMXMixin, ListView):
    partial_template = 'products/partials/review_list.html'
    full_template = 'products/review_list.html'
    paginate_by = 10
    context_object_name = 'reviews'
    
    def test_func(self) -> bool | None:
        return self.request.user.is_staff
    
    def get_queryset(self):
        qs = Review.objects.all().order_by('-created_at')
        
        approved = self.request.GET.get('approved')
        product_id = self.request.GET.get('product')
        
        if approved is not None:
            qs = qs.filter(approved=approved)
        if product_id:
            qs = qs.filter(product_id=product_id)
            
        return qs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx
    
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        ctx = self.get_context_data()
        return self.render_response(ctx)
    

class ApproveReview(UserPassesTestMixin, View):
    def test_func(self) -> bool | None:
        return self.request.user.is_staff
    
    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)
        review.approved = True
        review.save()
        ctx = {
            'review': review,
            'message': 'Approved!'
        }
        return TemplateResponse(request, 'products/partials/review_row.html', ctx)


class RejectReview(UserPassesTestMixin, View):
    def test_func(self) -> bool | None:
        return self.request.user.is_staff
    
    def post(self, request, pk, *args, **kwargs):
        review = get_object_or_404(Review, pk=pk)
        review.approved = False
        review.save()
        ctx = {
            'review': review,
            'message': 'Rejected!'
        }
        return TemplateResponse(request, 'products/partials/review_row.html', ctx)
