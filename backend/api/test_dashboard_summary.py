from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Organization
from api.permissions import ROLE_VIEWER


class DashboardSummaryTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="VisionX Workspace",
            slug="visionx-workspace",
        )
        self.user = get_user_model().objects.create_user(
            username="dashboard-viewer",
            password="test-password",
            organization=self.organization,
        )
        self.user.groups.add(Group.objects.get_or_create(name=ROLE_VIEWER)[0])
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_viewer_can_load_summary_with_recording_counts(self):
        response = self.client.get("/api/dashboard/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["counts"]["recordings"], 0)
