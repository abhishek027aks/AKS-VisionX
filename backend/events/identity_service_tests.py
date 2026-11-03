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


class IdentityServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Phase 5 Identity Organization",
            slug="phase-5-identity-organization",
        )

        cls.other_organization = Organization.objects.create(
            name="Phase 5 Other Organization",
            slug="phase-5-other-organization",
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="Phase 5 Identity Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

        cls.session = TrackingSession.objects.create(
            organization=cls.organization,
            camera=cls.camera,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id="person-501",
            status=TrackingSession.Status.ACTIVE,
            first_seen_at="2026-08-19T08:00:00Z",
            last_seen_at="2026-08-19T08:00:00Z",
            label="person",
            total_detections=1,
        )

        cls.person = PersonProfile.objects.create(
            organization=cls.organization,
            name="Test Person",
            category=PersonProfile.Category.EMPLOYEE,
        )

        cls.vehicle = VehicleProfile.objects.create(
            organization=cls.organization,
            name="Test Vehicle",
            category=VehicleProfile.Category.EMPLOYEE,
            vehicle_type=VehicleProfile.VehicleType.CAR,
            registration_number="TEST-001",
        )

        cls.other_person = PersonProfile.objects.create(
            organization=cls.other_organization,
            name="Other Organization Person",
            category=PersonProfile.Category.OTHER,
        )

    def test_link_person_identity_creates_match(self):
        match = link_person_identity(
            tracking_session=self.session,
            person_profile=self.person,
            match_method=IdentityMatch.MatchMethod.MANUAL,
            confidence=Decimal("0.95"),
            confirmed=True,
            metadata={
                "source": "phase5-test",
            },
        )

        self.assertIsNotNone(match)

        self.assertEqual(
            IdentityMatch.objects.count(),
            1,
        )

        self.assertEqual(
            match.organization,
            self.organization,
        )

        self.assertEqual(
            match.tracking_session,
            self.session,
        )

        self.assertEqual(
            match.person_profile,
            self.person,
        )

        self.assertEqual(
            match.identity_type,
            IdentityMatch.IdentityType.PERSON,
        )

        self.assertEqual(
            match.match_method,
            IdentityMatch.MatchMethod.MANUAL,
        )

        self.assertEqual(
            match.confidence,
            Decimal("0.95"),
        )

        self.assertTrue(
            match.is_confirmed,
        )

        self.assertEqual(
            match.metadata["source"],
            "phase5-test",
        )

        self.session.refresh_from_db()

        self.assertEqual(
            self.session.person_profile,
            self.person,
        )

        self.assertEqual(
            self.session.label,
            "Test Person",
        )

    def test_link_vehicle_identity_creates_match(self):
        vehicle_session = TrackingSession.objects.create(
            organization=self.organization,
            camera=self.camera,
            object_type=TrackingSession.ObjectType.VEHICLE,
            tracking_id="vehicle-501",
            status=TrackingSession.Status.ACTIVE,
            first_seen_at="2026-08-19T08:00:00Z",
            last_seen_at="2026-08-19T08:00:00Z",
            label="car",
            total_detections=1,
        )

        match = link_vehicle_identity(
            tracking_session=vehicle_session,
            vehicle_profile=self.vehicle,
            match_method=IdentityMatch.MatchMethod.PLATE,
            confidence=Decimal("0.98"),
            confirmed=True,
            metadata={
                "plate": "TEST-001",
            },
        )

        self.assertIsNotNone(match)

        self.assertEqual(
            match.organization,
            self.organization,
        )

        self.assertEqual(
            match.tracking_session,
            vehicle_session,
        )

        self.assertEqual(
            match.vehicle_profile,
            self.vehicle,
        )

        self.assertEqual(
            match.identity_type,
            IdentityMatch.IdentityType.VEHICLE,
        )

        self.assertEqual(
            match.match_method,
            IdentityMatch.MatchMethod.PLATE,
        )

        self.assertEqual(
            match.confidence,
            Decimal("0.98"),
        )

        vehicle_session.refresh_from_db()

        self.assertEqual(
            vehicle_session.vehicle_profile,
            self.vehicle,
        )

        self.assertEqual(
            vehicle_session.label,
            "Test Vehicle",
        )

    def test_person_identity_rejects_different_organization(self):
        with self.assertRaises(ValueError):
            link_person_identity(
                tracking_session=self.session,
                person_profile=self.other_person,
            )

        self.assertEqual(
            IdentityMatch.objects.count(),
            0,
        )

        self.session.refresh_from_db()

        self.assertIsNone(
            self.session.person_profile,
        )

    def test_vehicle_identity_rejects_different_organization(self):
        other_camera = Camera.objects.create(
            organization=self.other_organization,
            name="Other Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

        other_session = TrackingSession.objects.create(
            organization=self.other_organization,
            camera=other_camera,
            object_type=TrackingSession.ObjectType.VEHICLE,
            tracking_id="vehicle-other",
            status=TrackingSession.Status.ACTIVE,
            first_seen_at="2026-08-19T08:00:00Z",
            last_seen_at="2026-08-19T08:00:00Z",
            label="car",
            total_detections=1,
        )

        with self.assertRaises(ValueError):
            link_vehicle_identity(
                tracking_session=other_session,
                vehicle_profile=self.vehicle,
            )

        self.assertEqual(
            IdentityMatch.objects.count(),
            0,
        )

    def test_person_identity_defaults_to_empty_metadata(self):
        match = link_person_identity(
            tracking_session=self.session,
            person_profile=self.person,
        )

        self.assertEqual(
            match.metadata,
            {},
        )

        self.assertEqual(
            match.match_method,
            IdentityMatch.MatchMethod.MANUAL,
        )

        self.assertTrue(
            match.is_confirmed,
        )

    def test_vehicle_identity_defaults_to_empty_metadata(self):
        vehicle_session = TrackingSession.objects.create(
            organization=self.organization,
            camera=self.camera,
            object_type=TrackingSession.ObjectType.VEHICLE,
            tracking_id="vehicle-502",
            status=TrackingSession.Status.ACTIVE,
            first_seen_at="2026-08-19T08:00:00Z",
            last_seen_at="2026-08-19T08:00:00Z",
            label="car",
            total_detections=1,
        )

        match = link_vehicle_identity(
            tracking_session=vehicle_session,
            vehicle_profile=self.vehicle,
        )

        self.assertEqual(
            match.metadata,
            {},
        )

        self.assertEqual(
            match.match_method,
            IdentityMatch.MatchMethod.MANUAL,
        )

        self.assertTrue(
            match.is_confirmed,
        )
