import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Organization
from api.permissions import ROLE_VIEWER
from audit.models import AuditLog


User = get_user_model()


class RegistrationThrottle(AnonRateThrottle):
    scope = "auth_registration"


def _client_metadata(request):
    return {
        "ip_address": request.META.get("REMOTE_ADDR"),
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
    }


def _record_auth_event(request, user, method, result, description):
    AuditLog.objects.create(
        user=user,
        organization=user.organization if user else None,
        action=AuditLog.Action.LOGIN,
        result=result,
        description=description,
        metadata={"authentication": method},
        **_client_metadata(request),
    )


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def _create_viewer_workspace(user, workspace_name):
    slug_prefix = slugify(user.username)[:180] or "workspace"
    organization = Organization.objects.create(
        name=workspace_name[:200],
        slug=f"{slug_prefix}-{uuid.uuid4().hex[:12]}",
    )
    user.organization = organization
    user.save(update_fields=["organization"])
    viewer_group, _ = Group.objects.get_or_create(name=ROLE_VIEWER)
    user.groups.add(viewer_group)


def _unique_username(base):
    base = (base or "google-user")[:150]
    username = base
    suffix = 1
    while User.objects.filter(username__iexact=username).exists():
        suffix_text = str(suffix)
        username = f"{base[:150 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return username


@api_view(["GET"])
@permission_classes([AllowAny])
def google_auth_config(request):
    return Response({"client_id": getattr(settings, "GOOGLE_CLIENT_ID", "")})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([RegistrationThrottle])
def register(request):
    username = str(request.data.get("username", "")).strip()
    email = str(request.data.get("email", "")).strip().lower()
    password = request.data.get("password", "")
    password_confirm = request.data.get("password_confirm", "")

    errors = {}
    if not username:
        errors["username"] = ["Username is required."]
    elif len(username) > 150:
        errors["username"] = ["Username must be 150 characters or fewer."]
    elif User.objects.filter(username__iexact=username).exists():
        errors["username"] = ["This username is already in use."]

    if not email:
        errors["email"] = ["Email is required."]
    else:
        try:
            validate_email(email)
        except DjangoValidationError:
            errors["email"] = ["Enter a valid email address."]
        if User.objects.filter(email__iexact=email).exists():
            errors["email"] = ["An account with this email already exists."]

    if password != password_confirm:
        errors["password_confirm"] = ["Passwords do not match."]
    try:
        validate_password(password, user=User(username=username, email=email))
    except DjangoValidationError as exc:
        errors["password"] = list(exc.messages)

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
            _create_viewer_workspace(user, f"{username}'s workspace")
    except IntegrityError:
        return Response(
            {"detail": "An account with these details already exists."},
            status=status.HTTP_409_CONFLICT,
        )

    _record_auth_event(
        request,
        user,
        "password_registration",
        AuditLog.Result.SUCCESS,
        "User registered and signed in.",
    )
    return Response(
        {"user": {"username": user.username, "email": user.email}, **_tokens_for_user(user)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([RegistrationThrottle])
def google_auth(request):
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    if not client_id:
        return Response(
            {"detail": "Google sign-in is not configured on this server."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    credential = request.data.get("credential")
    if not isinstance(credential, str) or not credential:
        return Response(
            {"detail": "A Google ID token is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            audience=client_id,
        )
    except ValueError:
        _record_auth_event(
            request,
            None,
            "google",
            AuditLog.Result.FAILURE,
            "Google sign-in failed token verification.",
        )
        return Response(
            {"detail": "The Google credential is invalid or expired."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    except GoogleAuthError:
        _record_auth_event(
            request,
            None,
            "google",
            AuditLog.Result.FAILURE,
            "Google sign-in could not reach the token verifier.",
        )
        return Response(
            {"detail": "Google verification is temporarily unavailable."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    email = str(claims.get("email", "")).strip().lower()
    subject = str(claims.get("sub", "")).strip()
    verified = claims.get("email_verified") is True or str(
        claims.get("email_verified", "")
    ).lower() == "true"
    if not verified or not email or not subject:
        _record_auth_event(
            request,
            None,
            "google",
            AuditLog.Result.FAILURE,
            "Google sign-in requires a verified email address.",
        )
        return Response(
            {"detail": "Sign in with a Google account that has a verified email."},
            status=status.HTTP_403_FORBIDDEN,
        )

    display_name = str(claims.get("name", "")).strip()
    name_parts = display_name.split(maxsplit=1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    try:
        with transaction.atomic():
            user = User.objects.select_for_update().filter(
                google_subject=subject
            ).first()

            if user is None:
                user = User.objects.select_for_update().filter(
                    email__iexact=email
                ).first()
            created = user is None

            if user is not None and user.google_subject not in (None, subject):
                return Response(
                    {"detail": "This email is already linked to another Google account."},
                    status=status.HTTP_409_CONFLICT,
                )

            if user is None:
                username = _unique_username(email.split("@", 1)[0])
                user = User(
                    username=username,
                    email=email,
                    google_subject=subject,
                    first_name=first_name,
                    last_name=last_name,
                )
                user.set_unusable_password()
            else:
                user.google_subject = subject
                if user.email.casefold() != email.casefold():
                    if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                        return Response(
                            {"detail": "This Google email is already used by another account."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    user.email = email
                if not user.first_name:
                    user.first_name = first_name
                if not user.last_name:
                    user.last_name = last_name

            if not user.is_active:
                return Response(
                    {"detail": "This account is inactive. Contact an administrator."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            user.save()
            if created:
                _create_viewer_workspace(
                    user,
                    f"{display_name or email}'s workspace",
                )
    except IntegrityError:
        return Response(
            {"detail": "Unable to link this Google account to a user."},
            status=status.HTTP_409_CONFLICT,
        )

    _record_auth_event(
        request,
        user,
        "google",
        AuditLog.Result.SUCCESS,
        "User signed in with Google.",
    )
    return Response(
        {"user": {"username": user.username, "email": user.email}, **_tokens_for_user(user)}
    )
