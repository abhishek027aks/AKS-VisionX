from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from accounts.models import Organization
from cameras.models import Camera
from events.models import (
    IdentityMatch,
    PersonProfile,
    TrackingSession,
)

from events.identity_service import link_person_identity


User = get_user_model()


class TrackingSummaryAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Phase 5 API Organization",
            slug="phase-5-api-organization",
        )

        cls.other_organization = Organization.objects.create(
            name="Phase 5 API Other Organization",
            slug="phase-5-api-other-organization",
        )

        cls.viewer_group, _ = Group.objects.get_or_create(name="Viewer")

        cls.user = User.objects.create_user(
            username="phase5apiuser",
            password="TestPassword123!",
            organization=cls.organization,
        )

        cls.user.groups.add(
            cls.viewer_group
        )

        cls.other_user = User.objects.create_user(
            username="phase5apiotheruser",
            password="TestPassword123!",
            organization=cls.other_organization,
        )

        cls.other_user.groups.add(
            cls.viewer_group
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="Phase 5 API Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

        cls.other_camera = Camera.objects.create(
            organization=cls.other_organization,
            name="Other API Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

        cls.person = PersonProfile.objects.create(
            organization=cls.organization,
            name="API Test Person",
            category=PersonProfile.Category.EMPLOYEE,
        )

    def setUp(self):
        self.client = APIClient()

    def create_session(
        self,
        tracking_id="api-person-1",
        organization=None,
        camera=None,
        label="person",
    ):
        organization = organization or self.organization
        camera = camera or self.camera

        occurred_at = timezone.now()

        return TrackingSession.objects.create(
            organization=organization,
            camera=camera,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id=tracking_id,
            status=TrackingSession.Status.ACTIVE,
            first_seen_at=occurred_at,
            last_seen_at=occurred_at,
            label=label,
            total_detections=1,
            total_distance=Decimal("0"),
            camera_count=1,
            zone_count=1,
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(
            user=user or self.user
        )

    def test_tracking_summary_requires_authentication(self):
        session = self.create_session(
            tracking_id="auth-required-1",
        )

        response = self.client.get(
            reverse(
                "tracking-session-summary",
                kwargs={
                    "tracking_id": session.tracking_id,
                },
            )
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )

    def test_tracking_summary_returns_latest_session(self):
        older = self.create_session(
            tracking_id="latest-session-1",
            label="older",
        )

        older.status = TrackingSession.Status.ENDED

        older.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        newer = self.create_session(
            tracking_id="latest-session-1",
            label="newer",
        )

        self.authenticate()

        response = self.client.get(
            reverse(
                "tracking-session-summary",
                kwargs={
                    "tracking_id": "latest-session-1",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["session"]["id"],
            newer.id,
        )

        self.assertEqual(
            response.data["session"]["label"],
            "newer",
        )

    def test_tracking_summary_includes_identity_history(self):
        session = self.create_session(
            tracking_id="identity-api-1",
        )

        link_person_identity(
            tracking_session=session,
            person_profile=self.person,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=Decimal("0.96"),
            confirmed=True,
            metadata={
                "source": "api-test",
            },
        )

        self.authenticate()

        response = self.client.get(
            reverse(
                "tracking-session-summary",
                kwargs={
                    "tracking_id": "identity-api-1",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["session"]["label"],
            "API Test Person",
        )

        self.assertEqual(
            len(response.data["identities"]),
            1,
        )

        identity = response.data["identities"][0]

        self.assertEqual(
            identity["identity_type"],
            "PERSON",
        )

        self.assertEqual(
            identity["match_method"],
            "FACE",
        )

        self.assertEqual(
            identity["person"],
            "API Test Person",
        )

        self.assertIsNone(
            identity["vehicle"],
        )

        self.assertEqual(
            str(identity["confidence"]),
            "0.96",
        )

        self.assertTrue(
            identity["is_confirmed"],
        )

        self.assertEqual(
            identity["metadata"]["source"],
            "api-test",
        )

    def test_tracking_summary_hides_other_organization(self):
        self.create_session(
            tracking_id="private-other-org-1",
            organization=self.other_organization,
            camera=self.other_camera,
            label="other-org-person",
        )

        self.authenticate()

        response = self.client.get(
            reverse(
                "tracking-session-summary",
                kwargs={
                    "tracking_id": "private-other-org-1",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_tracking_summary_unknown_tracking_id_returns_404(self):
        self.authenticate()

        response = self.client.get(
            reverse(
                "tracking-session-summary",
                kwargs={
                    "tracking_id": "does-not-exist",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_user_from_other_organization_cannot_access_session(self):
        session = self.create_session(
            tracking_id="organization-isolation-1",
        )

        self.authenticate(
            self.other_user,
        )

        response = self.client.get(
            reverse(
                "tracking-session-summary",
                kwargs={
                    "tracking_id": session.tracking_id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

