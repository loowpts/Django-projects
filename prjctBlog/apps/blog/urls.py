from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.PostListView.as_view(), name='post_list'),
    path('category/<slug:category_slug>/', views.PostListView.as_view(), name='post_list_by_category'),
    path('tag/<slug:tag_slug>/', views.PostListView.as_view(), name='post_list_by_tag'),
    path('post/create/', views.PostCreateView.as_view(), name='post_create'),
    path('post/<slug:slug>/', views.PostDetailView.as_view(), name='post_detail'),
    path('post/<slug:slug>/edit/', views.PostUpdateView.as_view(), name='post_update'),
    path('post/<slug:slug>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    
    path('post/<slug:slug>/comment/add/', views.CommentCreateView.as_view(), name='comment_create'),
    path('comment/<int:pk>/edit/', views.CommentUpdateView.as_view(), name='comment_update'),
    path('comment/<int:pk>/delete/', views.CommentDeleteView.as_view(), name='comment_delete'),
    
    path('post/<slug:post_slug>/like/', views.LikeCreateView.as_view(), name='post_like'),
    path('post/<slug:post_slug>/unlike/', views.LikeDeleteView.as_view(), name='post_unlike'),
    path('comment/<int:comment_id>/like/', views.LikeCreateView.as_view(), name='comment_like'),
    path('comment/<int:comment_id>/unlike/', views.LikeDeleteView.as_view(), name='comment_unlike'),
    
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscription_list'),
    path('category/<slug:category_slug>/subscribe/', views.SubscriptionView.as_view(), name='category_subscribe'),
    path('category/<slug:category_slug>/unsubscribe/', views.SubscriptionDeleteView.as_view(), name='category_unsubscribe'),
]
