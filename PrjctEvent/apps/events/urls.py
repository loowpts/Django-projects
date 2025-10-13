from django.urls import path
from .views import (
    EventListView, EventDetailView, EventCreateView, EventUpdateView, EventDeleteView,
    EventArchiveView, ReviewCreateView, ReviewUpdateView, ReviewDeleteView,
    ReviewListView, ApproveReviewView, RejectReviewView
)

app_name = 'events'

urlpatterns = [
    path('', EventListView.as_view(), name='event_list'),
    path('<slug:slug>/', EventDetailView.as_view(), name='event_detail'),
    path('create/', EventCreateView.as_view(), name='event_create'),
    path('<slug:slug>/update/', EventUpdateView.as_view(), name='event_update'),
    path('<slug:slug>/delete/', EventDeleteView.as_view(), name='event_delete'),
    path('archive/', EventArchiveView.as_view(), name='event_archive'),
    path('<slug:slug>/review/create/', ReviewCreateView.as_view(), name='review_create'),
    path('review/<int:pk>/update/', ReviewUpdateView.as_view(), name='review_update'),
    path('review/<int:pk>/delete/', ReviewDeleteView.as_view(), name='review_delete'),
    path('reviews/', ReviewListView.as_view(), name='review_list'),
    path('review/<int:pk>/approve/', ApproveReviewView.as_view(), name='review_approve'),
    path('review/<int:pk>/reject/', RejectReviewView.as_view(), name='review_reject'),
]