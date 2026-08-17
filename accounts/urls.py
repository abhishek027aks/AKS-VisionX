from django.urls import path

from .views import (
    UserLoginView,
    UserLogoutView,
    UserPasswordChangeView,
    UserPasswordResetCompleteView,
    UserPasswordResetConfirmView,
    UserPasswordResetDoneView,
    UserPasswordResetView,
    dashboard_view,
    password_change_done_view,
    profile_view,
    register_view,
    security_view,
)


app_name = "accounts"


urlpatterns = [
    path(
        "register/",
        register_view,
        name="register",
    ),

    path(
        "login/",
        UserLoginView.as_view(),
        name="login",
    ),

    path(
        "logout/",
        UserLogoutView.as_view(),
        name="logout",
    ),

    path(
        "dashboard/",
        dashboard_view,
        name="dashboard",
    ),

    path(
        "profile/",
        profile_view,
        name="profile",
    ),

    path(
        "security/",
        security_view,
        name="security",
    ),

    path(
        "security/password/",
        UserPasswordChangeView.as_view(),
        name="password_change",
    ),

    path(
        "security/password/done/",
        password_change_done_view,
        name="password_change_done",
    ),

    path(
        "password-reset/",
        UserPasswordResetView.as_view(),
        name="password_reset",
    ),

    path(
        "password-reset/done/",
        UserPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),

    path(
        "password-reset/confirm/<uidb64>/<token>/",
        UserPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),

    path(
        "password-reset/complete/",
        UserPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
