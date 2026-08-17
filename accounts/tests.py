from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import UserProfile


User = get_user_model()


class AccountsTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="StrongTest@2026",
            first_name="Test",
            last_name="User",
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            mobile="9876543210",
        )

    def test_user_profile_exists(self):
        self.assertEqual(
            self.user.profile,
            self.profile,
        )

    def test_login_page(self):
        response = self.client.get(
            reverse("accounts:login")
        )

        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "/accounts/login/",
            response.url,
        )

    def test_profile_requires_login(self):
        response = self.client.get(
            reverse("accounts:profile")
        )

        self.assertEqual(response.status_code, 302)

    def test_security_requires_login(self):
        response = self.client.get(
            reverse("accounts:security")
        )

        self.assertEqual(response.status_code, 302)

    def test_logged_in_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "testuser",
        )

    def test_logged_in_profile(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("accounts:profile")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "9876543210",
        )

    def test_security_page(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("accounts:security")
        )

        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "testuser",
                "password": "StrongTest@2026",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("accounts:dashboard"),
        )

    def test_login_failure(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "testuser",
                "password": "WrongPassword@2026",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Username or password is incorrect.",
        )

    def test_logout(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:logout")
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("accounts:login"),
        )

    def test_password_change(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "StrongTest@2026",
                "new_password1": "NewStrong@2026",
                "new_password2": "NewStrong@2026",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                "NewStrong@2026"
            )
        )

    def test_registration(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "mobile": "9999999999",
                "password1": "StrongNew@2026",
                "password2": "StrongNew@2026",
            },
        )

        self.assertEqual(response.status_code, 302)

        new_user = User.objects.get(
            username="newuser"
        )

        self.assertTrue(
            UserProfile.objects.filter(
                user=new_user
            ).exists()
        )

    def test_authenticated_user_cannot_open_register(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("accounts:register")
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("accounts:dashboard"),
        )
