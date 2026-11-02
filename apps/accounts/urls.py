from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.AppLoginView.as_view(), name="login"),
    path("logout/", views.AppLogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
]
