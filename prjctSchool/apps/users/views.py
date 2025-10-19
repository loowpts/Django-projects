from django.db.models.base import Model as Model
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import FormView, DetailView
from .models import UserProfile
from .forms import RegisterForm, UserProfileForm, LoginForm
from django.core.exceptions import PermissionDenied


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = LoginForm


class RegisterView(FormView):
    template_name = 'users/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('users:my_profile')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, 'Добро пожаловать! Аккаунт создан и выполнен вход.')
        return super().form_valid(form)


class MyProfileView(LoginRequiredMixin, DetailView):
    model = UserProfile
    template_name = 'users/my_profile.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        if pk is None or pk == 'me':
            profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
            return profile
        return get_object_or_404(UserProfile.objects.select_related('user'), user__pk=pk)


class UserProfileDetailView(DetailView):
    model = UserProfile
    template_name = 'users/profile_detail.html'
    context_object_name = 'profile'

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
    form_class = UserProfileForm
    template_name = 'users/profile_update.html'
    success_url = reverse_lazy('users:my_profile')

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def form_valid(self, form):
        messages.success(self.request, 'Профиль успешно обновлён.')
        return super().form_valid(form)
    

