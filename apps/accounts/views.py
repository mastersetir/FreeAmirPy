from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render
from django.urls import reverse_lazy

from .forms import LoginForm

class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm

class AppLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")

@login_required
def profile(request):
    return render(request, "accounts/profile.html")
