from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Organization
from api.permissions import ROLE_VIEWER
from audit.models import AuditLog


User = get_user_model()
STRONG_PASSWORD = "T4test-Passphrase-long-Unique!"


class AccountRegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"
        self.payload = {
            "username": "new-vision-user",
            "email": "new-user@example.test",
            "password": STRONG_PASSWORD,
            "password_confirm": STRONG_PASSWORD,
        }

    def test_registration_creates_viewer_workspace_and_tokens(self):
        response = self.client.post(
            "/api/auth/register/",
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        user = User.objects.get(username="new-vision-user")
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertIsNotNone(user.organization)
        self.assertTrue(user.groups.filter(name=ROLE_VIEWER).exists())
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(
            AuditLog.objects.filter(
                user=user,
                action=AuditLog.Action.LOGIN,
                result=AuditLog.Result.SUCCESS,
            ).exists()
        )

    def test_registration_rejects_duplicate_username_and_email(self):
        User.objects.create_user(
            username="new-vision-user",
            email="new-user@example.test",
            password=STRONG_PASSWORD,
        )

        response = self.client.post(
            "/api/auth/register/",
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)
        self.assertIn("email", response.data)

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            "/api/auth/register/",
            {**self.payload, "password_confirm": "different-password"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirm", response.data)
        self.assertFalse(User.objects.filter(username="new-vision-user").exists())

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                **self.payload,
                "password": "short",
                "password_confirm": "short",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)


@override_settings(GOOGLE_CLIENT_ID="visionx-client-id")
class GoogleAuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"
        self.payload = {"credential": "test-google-id-token"}
        self.claims = {
            "sub": "google-user-subject",
            "email": "google-user@example.test",
            "email_verified": True,
            "name": "Google Vision User",
        }

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_verified_google_user_is_registered_as_viewer(
        self,
        verify_token,
    ):
        verify_token.return_value = self.claims

        response = self.client.post(
            "/api/auth/google/",
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        user = User.objects.get(email="google-user@example.test")
        self.assertEqual(user.google_subject, "google-user-subject")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.first_name, "Google")
        self.assertEqual(user.last_name, "Vision User")
        self.assertTrue(user.groups.filter(name=ROLE_VIEWER).exists())
        verify_token.assert_called_once()

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_unverified_google_email_is_rejected(self, verify_token):
        verify_token.return_value = {
            **self.claims,
            "email_verified": False,
        }

        response = self.client.post(
            "/api/auth/google/",
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.exists())

    @patch(
        "google.oauth2.id_token.verify_oauth2_token",
        side_effect=ValueError("Invalid token"),
    )
    def test_invalid_google_token_is_rejected_and_audited(self, verify_token):
        response = self.client.post(
            "/api/auth/google/",
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(User.objects.exists())
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.LOGIN,
                result=AuditLog.Result.FAILURE,
                metadata__authentication="google",
            ).exists()
        )
        verify_token.assert_called_once()

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_verified_google_email_links_existing_password_account(
        self,
        verify_token,
    ):
        organization = Organization.objects.create(
            name="Existing workspace",
            slug="existing-workspace",
        )
        user = User.objects.create_user(
            username="existing-password-user",
            email="google-user@example.test",
            password=STRONG_PASSWORD,
            organization=organization,
        )
        verify_token.return_value = self.claims

        response = self.client.post(
            "/api/auth/google/",
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.google_subject, "google-user-subject")
        self.assertEqual(user.organization, organization)
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertEqual(User.objects.count(), 1)

    @override_settings(GOOGLE_CLIENT_ID="")
    def test_google_sign_in_requires_server_configuration(self):
        response = self.client.post(
            "/api/auth/google/",
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 503)

    @override_settings(GOOGLE_CLIENT_ID="")
    def test_google_config_reports_missing_client_id(self):
        response = self.client.get("/api/auth/google/config/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"client_id": ""})
