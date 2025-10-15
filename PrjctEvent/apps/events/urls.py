from django.urls import path
from .views import (
    EventList, EventDetail, EventCreate, EventUpdate, EventDelete,
    EventArchive, ReviewCreate, ReviewUpdate, ReviewDelete,
    ReviewList, ApproveReviewView, RejectReview
)

app_name = 'events'

urlpatterns = [
    path('', EventList.as_view(), name='event_list'),
    path('category/<slug:category_slug>/', EventList.as_view(), name='event_list_category'),
    path('<slug:slug>/', EventDetail.as_view(), name='event_detail'),
    path('create/', EventCreate.as_view(), name='event_create'),
    path('<slug:slug>/update/', EventUpdate.as_view(), name='event_update'),
    path('<slug:slug>/delete/', EventDelete.as_view(), name='event_delete'),
    path('archive/', EventArchive.as_view(), name='event_archive'),
    path('<slug:event_slug>/reviews/create/', ReviewCreate.as_view(), name='review_create'),
    path('reviews/<int:pk>/update/', ReviewUpdate.as_view(), name='review_update'),
    path('reviews/<int:pk>/delete/', ReviewDelete.as_view(), name='review_delete'),
    path('reviews/', ReviewList.as_view(), name='review_list'),
    path('reviews/<int:pk>/approve/', ApproveReviewView.as_view(), name='review_approve'),
    path('reviews/<int:pk>/reject/', RejectReview.as_view(), name='review_reject'),
]