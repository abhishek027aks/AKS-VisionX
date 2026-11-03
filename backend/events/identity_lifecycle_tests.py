from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

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


class IdentityLifecycleTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Phase 5 Lifecycle Organization",
            slug="phase-5-lifecycle-organization",
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="Phase 5 Lifecycle Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

        cls.person_one = PersonProfile.objects.create(
            organization=cls.organization,
            name="Lifecycle Person One",
            category=PersonProfile.Category.EMPLOYEE,
        )

        cls.person_two = PersonProfile.objects.create(
            organization=cls.organization,
            name="Lifecycle Person Two",
            category=PersonProfile.Category.VISITOR,
        )

        cls.vehicle_one = VehicleProfile.objects.create(
            organization=cls.organization,
            name="Lifecycle Vehicle One",
            category=VehicleProfile.Category.PERSONAL,
            vehicle_type=VehicleProfile.VehicleType.CAR,
            registration_number="LIFE-001",
        )

    def create_session(
        self,
        tracking_id="lifecycle-1",
        object_type=TrackingSession.ObjectType.PERSON,
        label="person",
    ):
        occurred_at = timezone.now()

        return TrackingSession.objects.create(
            organization=self.organization,
            camera=self.camera,
            object_type=object_type,
            tracking_id=tracking_id,
            status=TrackingSession.Status.ACTIVE,
            first_seen_at=occurred_at,
            last_seen_at=occurred_at,
            label=label,
            total_detections=1,
        )

    def test_multiple_identity_matches_are_preserved(self):
        session = self.create_session(
            tracking_id="multi-identity-1",
        )

        first_match = link_person_identity(
            tracking_session=session,
            person_profile=self.person_one,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=Decimal("0.80"),
            confirmed=False,
            metadata={
                "stage": "initial",
            },
        )

        second_match = link_person_identity(
            tracking_session=session,
            person_profile=self.person_two,
            match_method=IdentityMatch.MatchMethod.MANUAL,
            confidence=Decimal("0.95"),
            confirmed=True,
            metadata={
                "stage": "confirmed",
            },
        )

        self.assertNotEqual(
            first_match.id,
            second_match.id,
        )

        self.assertEqual(
            IdentityMatch.objects.filter(
                tracking_session=session
            ).count(),
            2,
        )

        summary = get_tracking_session_summary(
            session
        )

        self.assertEqual(
            len(summary["identities"]),
            2,
        )

    def test_identity_summary_is_ordered_by_latest_match(self):
        session = self.create_session(
            tracking_id="identity-order-1",
        )

        older_time = timezone.now() - timedelta(
            seconds=30
        )

        older_match = IdentityMatch.objects.create(
            organization=self.organization,
            tracking_session=session,
            person_profile=self.person_one,
            identity_type=IdentityMatch.IdentityType.PERSON,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=Decimal("0.75"),
            matched_at=older_time,
            is_confirmed=False,
            metadata={
                "order": "older",
            },
        )

        newer_match = IdentityMatch.objects.create(
            organization=self.organization,
            tracking_session=session,
            person_profile=self.person_two,
            identity_type=IdentityMatch.IdentityType.PERSON,
            match_method=IdentityMatch.MatchMethod.MANUAL,
            confidence=Decimal("0.98"),
            matched_at=timezone.now(),
            is_confirmed=True,
            metadata={
                "order": "newer",
            },
        )

        summary = get_tracking_session_summary(
            session
        )

        self.assertEqual(
            len(summary["identities"]),
            2,
        )

        self.assertEqual(
            summary["identities"][0]["id"],
            newer_match.id,
        )

        self.assertEqual(
            summary["identities"][1]["id"],
            older_match.id,
        )

    def test_unconfirmed_identity_is_preserved(self):
        session = self.create_session(
            tracking_id="unconfirmed-1",
        )

        match = link_person_identity(
            tracking_session=session,
            person_profile=self.person_one,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=Decimal("0.60"),
            confirmed=False,
        )

        summary = get_tracking_session_summary(
            session
        )

        self.assertEqual(
            len(summary["identities"]),
            1,
        )

        self.assertFalse(
            summary["identities"][0]["is_confirmed"],
        )

        self.assertEqual(
            summary["identities"][0]["confidence"],
            Decimal("0.60"),
        )

        self.assertEqual(
            match.is_confirmed,
            False,
        )

    def test_vehicle_identity_is_preserved_in_summary(self):
        session = self.create_session(
            tracking_id="vehicle-lifecycle-1",
            object_type=TrackingSession.ObjectType.VEHICLE,
            label="car",
        )

        match = link_vehicle_identity(
            tracking_session=session,
            vehicle_profile=self.vehicle_one,
            match_method=IdentityMatch.MatchMethod.PLATE,
            confidence=Decimal("0.99"),
            confirmed=True,
        )

        summary = get_tracking_session_summary(
            session
        )

        self.assertEqual(
            len(summary["identities"]),
            1,
        )

        identity = summary["identities"][0]

        self.assertEqual(
            identity["id"],
            match.id,
        )

        self.assertEqual(
            identity["identity_type"],
            IdentityMatch.IdentityType.VEHICLE,
        )

        self.assertEqual(
            identity["vehicle"],
            "Lifecycle Vehicle One",
        )

        self.assertIsNone(
            identity["person"],
        )

    def test_identity_match_does_not_change_tracking_session_status(self):
        session = self.create_session(
            tracking_id="status-preservation-1",
        )

        link_person_identity(
            tracking_session=session,
            person_profile=self.person_one,
            match_method=IdentityMatch.MatchMethod.MANUAL,
            confidence=Decimal("0.90"),
            confirmed=True,
        )

        session.refresh_from_db()

        self.assertEqual(
            session.status,
            TrackingSession.Status.ACTIVE,
        )

    def test_identity_match_updates_session_label(self):
        session = self.create_session(
            tracking_id="label-update-1",
            label="person",
        )

        self.assertEqual(
            session.label,
            "person",
        )

        link_person_identity(
            tracking_session=session,
            person_profile=self.person_one,
        )

        session.refresh_from_db()

        self.assertEqual(
            session.label,
            "Lifecycle Person One",
        )
