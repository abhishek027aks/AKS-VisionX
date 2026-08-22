from decimal import Decimal

from django.test import TestCase

from accounts.models import Organization
from cameras.models import Camera

from events.models import (
    IdentityMatch,
    PersonProfile,
    TrackingSession,
    VehicleProfile,
)

from events.identity_service import (
    link_person_identity,
    link_vehicle_identity,
)

from events.tracking_summary_service import (
    get_tracking_session_summary,
)


class IdentityTrackingIntegrationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Phase 5 Integration Organization",
            slug="phase-5-integration-organization",
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="Phase 5 Integration Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

        cls.person = PersonProfile.objects.create(
            organization=cls.organization,
            name="Integration Person",
            category=PersonProfile.Category.EMPLOYEE,
        )

        cls.vehicle = VehicleProfile.objects.create(
            organization=cls.organization,
            name="Integration Vehicle",
            category=VehicleProfile.Category.PERSONAL,
            vehicle_type=VehicleProfile.VehicleType.CAR,
            registration_number="INT-001",
        )

    def create_session(
        self,
        tracking_id,
        object_type,
        label,
    ):
        return TrackingSession.objects.create(
            organization=self.organization,
            camera=self.camera,
            object_type=object_type,
            tracking_id=tracking_id,
            status=TrackingSession.Status.ACTIVE,
            first_seen_at="2026-08-19T08:00:00Z",
            last_seen_at="2026-08-19T08:00:00Z",
            label=label,
            total_detections=1,
        )

    def test_person_identity_appears_in_tracking_summary(self):
        session = self.create_session(
            tracking_id="person-integration-1",
            object_type=TrackingSession.ObjectType.PERSON,
            label="person",
        )

        link_person_identity(
            tracking_session=session,
            person_profile=self.person,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=Decimal("0.97"),
            confirmed=True,
            metadata={
                "source": "integration-test",
            },
        )

        summary = get_tracking_session_summary(
            session
        )

        self.assertEqual(
            summary["session"]["label"],
            "Integration Person",
        )

        self.assertEqual(
            len(summary["identities"]),
            1,
        )

        identity = summary["identities"][0]

        self.assertEqual(
            identity["identity_type"],
            IdentityMatch.IdentityType.PERSON,
        )

        self.assertEqual(
            identity["match_method"],
            IdentityMatch.MatchMethod.FACE,
        )

        self.assertEqual(
            identity["person"],
            "Integration Person",
        )

        self.assertIsNone(
            identity["vehicle"],
        )

        self.assertEqual(
            identity["confidence"],
            Decimal("0.97"),
        )

        self.assertTrue(
            identity["is_confirmed"],
        )

        self.assertEqual(
            identity["metadata"]["source"],
            "integration-test",
        )

    def test_vehicle_identity_appears_in_tracking_summary(self):
        session = self.create_session(
            tracking_id="vehicle-integration-1",
            object_type=TrackingSession.ObjectType.VEHICLE,
            label="car",
        )

        link_vehicle_identity(
            tracking_session=session,
            vehicle_profile=self.vehicle,
            match_method=IdentityMatch.MatchMethod.PLATE,
            confidence=Decimal("0.99"),
            confirmed=True,
            metadata={
                "plate": "INT-001",
            },
        )

        summary = get_tracking_session_summary(
            session
        )

        self.assertEqual(
            summary["session"]["label"],
            "Integration Vehicle",
        )

        self.assertEqual(
            len(summary["identities"]),
            1,
        )

        identity = summary["identities"][0]

        self.assertEqual(
            identity["identity_type"],
            IdentityMatch.IdentityType.VEHICLE,
        )

        self.assertEqual(
            identity["match_method"],
            IdentityMatch.MatchMethod.PLATE,
        )

        self.assertIsNone(
            identity["person"],
        )

        self.assertEqual(
            identity["vehicle"],
            "Integration Vehicle",
        )

        self.assertEqual(
            identity["confidence"],
            Decimal("0.99"),
        )

        self.assertTrue(
            identity["is_confirmed"],
        )

        self.assertEqual(
            identity["metadata"]["plate"],
            "INT-001",
        )

    def test_unidentified_tracking_session_has_empty_identity_history(self):
        session = self.create_session(
            tracking_id="unknown-integration-1",
            object_type=TrackingSession.ObjectType.PERSON,
            label="person",
        )

        summary = get_tracking_session_summary(
            session
        )

        self.assertEqual(
            summary["identities"],
            [],
        )

        self.assertIsNone(
            summary["session"]["label"]
            if summary["session"]["label"] is None
            else None,
        )
