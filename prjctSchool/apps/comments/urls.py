from django.urls import path
from .views import CommentCreateView, CommentDeleteView

app_name = 'comments'

urlpatterns = [
    path('lesson/<int:lesson_id>/comment/create/', CommentCreateView.as_view(), name='comment_create'),
    path('comment/<int:pk>/delete/', CommentDeleteView.as_view(), name='comment_delete'),
]