from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from .views import (
    CustomLoginView, MyProfileView, UserProfileDetailView,
    RegisterView, ProfileUpdateView,
)

app_name = 'users'

urlpatterns = [
    # auth
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('signup/', RegisterView.as_view(), name='signup'),  # Для совместимости с allauth

    # password reset
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='users/password_reset.html',
            email_template_name='users/password_reset_email.txt',
            subject_template_name='users/password_reset_subject.txt',
            success_url='/users/password-reset/done/'
        ),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
        name='password_reset_done'
    ),
    re_path(
        r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='users/password_reset_confirm.html',
            success_url='/users/reset/complete/'
        ),
        name='password_reset_confirm'
    ),
    path(
        'reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
        name='password_reset_complete'
    ),

    # my profile
    path('me/', MyProfileView.as_view(), name='my_profile'),
    path('me/edit/', ProfileUpdateView.as_view(), name='profile_update'),
    path('u/<int:pk>/', UserProfileDetailView.as_view(), name='profile_detail'),
]
