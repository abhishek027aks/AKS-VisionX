from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Organization
from api.permissions import ROLE_VIEWER
from cameras.models import Camera
from events.models import Detection, TrackingSession


class TrackingAnalyticsAPITests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Tracking Analytics Organization",
            slug="tracking-analytics-organization",
        )
        self.other_organization = Organization.objects.create(
            name="Other Tracking Analytics Organization",
            slug="other-tracking-analytics-organization",
        )
        self.user = get_user_model().objects.create_user(
            username="tracking-analytics-viewer",
            organization=self.organization,
        )
        self.user.groups.add(
            Group.objects.get_or_create(name=ROLE_VIEWER)[0]
        )
        self.camera = Camera.objects.create(
            organization=self.organization,
            name="Analytics Camera",
        )
        self.other_camera = Camera.objects.create(
            organization=self.other_organization,
            name="Other Analytics Camera",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def add_track(self, camera, object_type, label, tracking_id):
        now = timezone.now()
        return TrackingSession.objects.create(
            organization=camera.organization,
            camera=camera,
            object_type=object_type,
            tracking_id=tracking_id,
            label=label,
            first_seen_at=now,
            last_seen_at=now,
        )

    def test_daily_report_separates_detection_rows_from_tracks_and_scopes_org(
        self,
    ):
        animal_track = self.add_track(
            self.camera,
            TrackingSession.ObjectType.ANIMAL,
            "dog",
            "dog-1",
        )
        self.add_track(
            self.camera,
            TrackingSession.ObjectType.PERSON,
            "person",
            "person-1",
        )
        self.add_track(
            self.other_camera,
            TrackingSession.ObjectType.ANIMAL,
            "cow",
            "cow-outside-org",
        )
        now = timezone.now()
        for _ in range(3):
            Detection.objects.create(
                organization=self.organization,
                camera=self.camera,
                object_type=Detection.ObjectType.ANIMAL,
                label="dog",
                tracking_id="dog-1",
                first_seen_at=now,
                last_seen_at=now,
            )

        response = self.client.get("/api/analytics/tracking/?period=daily")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["counts"]["detections"], 3)
        self.assertEqual(response.data["counts"]["tracked_tracks"], 2)
        self.assertEqual(
            response.data["counts"]["tracked_tracks_by_type"],
            [
                {"object_type": "ANIMAL", "count": 1},
                {"object_type": "PERSON", "count": 1},
            ],
        )
        self.assertEqual(
            response.data["counts"]["animal_tracks_by_species"],
            [{"label": "dog", "count": 1}],
        )
        self.assertEqual(len(response.data["timeline"]), 24)
        self.assertIn("not verified entry/exit", response.data["count_semantics"])
        self.assertTrue(
            TrackingSession.objects.filter(pk=animal_track.pk).exists()
        )

    def test_report_rejects_unknown_period(self):
        response = self.client.get("/api/analytics/tracking/?period=yearly")

        self.assertEqual(response.status_code, 400)
        self.assertIn("daily, weekly, monthly", response.data["detail"])
