from django.db.models.base import Model as Model
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.core.exceptions import PermissionDenied
from .tasks import send_welcome_email_async
from allauth.account.views import SignupView, LoginView as AllauthLoginView

from .models import UserProfile
from .forms import RegisterForm, ProfileForm, LoginForm
from .models import User


class CustomLoginView(AllauthLoginView):
    template_name = 'account/login.html'
    authentication_form = LoginForm


class RegisterView(SignupView):
    template_name = 'account/signup.html'
    form_class = RegisterForm
    success_url = reverse_lazy('users:my_profile')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        send_welcome_email_async(user.email, user.first_name)
        messages.success(self.request, 'Добро пожаловать! Аккаунт создан и выполнен вход.')
        return super().form_valid(form)


class MyProfileView(LoginForm, DetailView):
    model = UserProfile
    template_name = 'users/my_profile.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        if pk is None or pk == 'me':
            return self.request.user.profile
        return get_object_or_404(User, pk=pk)


class UserProfileDetailView(DetailView):
    template_name = 'users/profile_detail.html'
    context_object_name = 'profile'
    model = UserProfile

    def get_object(self, queryset=None):
        profile = get_object_or_404(
            UserProfile.objects.select_related('user'),
            user__pk=self.kwargs['pk']
        )
        if not profile.is_public:
            if not self.request.user.is_authenticated or self.request.user.pk != profile.user_id:
                raise PermissionDenied("Профиль скрыт")
        return profile


class ProfileUpdateView(LoginRequiredMixin, DetailView):
    model = UserProfile
    template_name = 'users/profile_update.html'
    form_class = ProfileForm
    success_url = reverse_lazy('users:my_profile')

    def get_object(self, queryset=None):
        return get_object_or_404(UserProfile, user=self.request.user)
