from django.urls import path

from .views import CaptchaView, LoginView, LogoutView, MeView, RefreshView

app_name = "accounts"

urlpatterns = [
    path("captcha/", CaptchaView.as_view(), name="captcha"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]
