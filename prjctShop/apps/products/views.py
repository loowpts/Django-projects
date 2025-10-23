from typing import Any
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, DetailView
from django.http import HttpResponse
from django.template.response import TemplateResponse
from .models import Category, Product, Size
from django.db.models import Q


class IndexView(TemplateView):
    template_name = 'base.html'
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all()
        ctx['current_category'] = None
        return ctx
    
    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'content.html', ctx)
        return TemplateResponse(request, self.template_name, ctx)
    
    
class CatalogView(TemplateResponse):
    template_name = 'main/base.html'
    
    FILTER_MAPPING = {
        'color': lambda queryset, value: queryset.filter(color__iexact=value),
        'min_price': lambda queryset, value: queryset.filter(price_gte=value),
        'max_price': lambda queryset, value: queryset.filter(price_lte=value),
        'size': lambda queryset, value: queryset.filter(product_sizes__size__name=value),
    }
    
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        category_slug = kwargs.get('category_slug')
        categories = Category.objects.all()
        products = Product.objects.all().order_by('-created_at')
        current_category = None
        
        if category_slug:
            current_category = get_object_or_404(Category, slug=category_slug)
            products = products.filter(category=current_category)
            
        query = (self.request.GET.get('q') or '')
        if query:
            products = products.filter(
                Q(name__icontains=query | Q(description__icontains=query))
            )
        
        filter_params = {}
        for param, filter_func in self.FILTER_MAPPING.items():
            value = self.request.GET.get(param)
            if value:
                products = filter_func(products, value)
                filter_params[param] = value
            else:
                filter_params[param] = ''
                
        ctx.update({
            'categories': categories,
            'products': products,
            'current_category': category_slug,
            'sizes': Size.objects.all(),
            'search_query': query or ''
        })
        
        if self.request.GET.get('show_search') == 'true':
            ctx['show_search'] = True
        elif self.request.GET.get('reset_search') == 'true':
            ctx['reset_search'] = True
        
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            if ctx.get('show-search'):
                return TemplateResponse(request, 'main/search_input.html', ctx)
            elif ctx.get('reset-search'):
                return TemplateResponse(request, 'main/search_button.html', {})
            template = 'main/filter_modal.html' if request.GET.get('show_filters') == 'true' else 'main/catalog.html'
            return TemplateResponse(request, template, ctx)
        return TemplateResponse(request, self.template_name, ctx)


class ProductDetail(DetailView):
    model = Product
    template_name = 'main/base.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_contex_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.get_object()
        ctx['categories'] = Category.objects.all()
        ctx['related_products'] = Product.objects.filter(
            category=product.category
        ).exclude(id=product.id)[:4]
        ctx['current_category'] = product.category.slug
        return ctx
