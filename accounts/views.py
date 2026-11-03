from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import (
    UserProfileUpdateForm,
    UserRegistrationForm,
    UserUpdateForm,
)
from .models import UserProfile


def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            messages.success(
                request,
                "Your VyapaarX account has been created successfully.",
            )

            return redirect("accounts:dashboard")
    else:
        form = UserRegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = "accounts:login"


@login_required
def dashboard_view(request):
    return render(
        request,
        "accounts/dashboard.html",
    )


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        user_form = UserUpdateForm(
            request.POST,
            instance=request.user,
        )

        profile_form = UserProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=profile,
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()

            messages.success(
                request,
                "Profile updated successfully.",
            )

            return redirect("accounts:profile")
    else:
        user_form = UserUpdateForm(
            instance=request.user
        )

        profile_form = UserProfileUpdateForm(
            instance=profile
        )

    return render(
        request,
        "accounts/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
        },
    )


@login_required
def security_view(request):
    return render(
        request,
        "accounts/security.html",
    )


class UserPasswordChangeView(
    LoginRequiredMixin,
    PasswordChangeView,
):
    template_name = "accounts/password_change.html"
    form_class = PasswordChangeForm
    success_url = reverse_lazy(
        "accounts:password_change_done"
    )


@login_required
def password_change_done_view(request):
    messages.success(
        request,
        "Your password was changed successfully.",
    )

    return render(
        request,
        "accounts/password_change_done.html",
    )


class UserPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy(
        "accounts:password_reset_done"
    )


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy(
        "accounts:password_reset_complete"
    )


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
