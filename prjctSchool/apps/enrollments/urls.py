from django.urls import path
from .views import EnrollmentCreateView

app_name = 'enrollments'

urlpatterns = [
    path('course/<int:course_id>/enroll/', EnrollmentCreateView.as_view(), name='enroll'),
]