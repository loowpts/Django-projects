from django.urls import path
from . import views

app_name = 'todo'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('create/', views.TaskCreateView.as_view(), name='task_create'),
    path('task/<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('<int:pk>/update/', views.TaskUpdateView.as_view(), name='task_update'),
    path('<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    path('<int:pk>/toggle/', views.ToggleTaskDoneView.as_view(), name='task_toggle_done'),
    path('<int:pk>/change/<str:new_status>/', views.TaskChangeView.as_view(), name='task_change'),
    path('<int:pk>/archive/', views.TaskArchiveView.as_view(), name='task_archive'),
    path('<int:pk>/duplicate/', views.DuplicateTaskView.as_view(), name='task_duplicate'),
]