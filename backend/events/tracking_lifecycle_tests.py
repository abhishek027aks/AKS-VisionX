from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import Organization
from cameras.models import Camera
from events.models import (
    Detection,
    TrackingCameraVisit,
    TrackingLocation,
    TrackingPoint,
    TrackingSession,
)

from events.tracking_service import update_tracking_session
from events.tracking_end_service import end_stale_tracking_sessions
from events.tracking_summary_service import get_tracking_session_summary


class TrackingLifecycleTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Phase 4 Tracking Organization",
            slug="phase-4-tracking-organization",
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="Phase 4 Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

    def create_detection(
        self,
        tracking_id="1",
        occurred_at=None,
        x="0.100000",
        y="0.100000",
        zone="Zone A",
    ):
        occurred_at = (
            occurred_at
            or timezone.now()
        )

        return Detection.objects.create(
            organization=self.organization,
            camera=self.camera,
            object_type="PERSON",
            label="person",
            confidence=Decimal("0.90"),
            tracking_id=tracking_id,
            status=Detection.DetectionStatus.ACTIVE,
            first_seen_at=occurred_at,
            last_seen_at=occurred_at,
            bbox_x=Decimal(x),
            bbox_y=Decimal(y),
            bbox_width=Decimal("0.200000"),
            bbox_height=Decimal("0.300000"),
            metadata={
                "zone": zone,
            },
        )

    def test_stale_session_is_ended(self):
        old_time = (
            timezone.now()
            - timedelta(seconds=60)
        )

        detection = self.create_detection(
            tracking_id="100",
            occurred_at=old_time,
            zone="Zone A",
        )

        session = update_tracking_session(
            detection
        )

        self.assertEqual(
            session.status,
            TrackingSession.Status.ACTIVE,
        )

        ended_count = end_stale_tracking_sessions(
            timeout_seconds=30
        )

        self.assertEqual(
            ended_count,
            1,
        )

        session.refresh_from_db()

        self.assertEqual(
            session.status,
            TrackingSession.Status.ENDED,
        )

    def test_stale_session_closes_location(self):
        old_time = (
            timezone.now()
            - timedelta(seconds=60)
        )

        detection = self.create_detection(
            tracking_id="101",
            occurred_at=old_time,
            zone="Zone A",
        )

        session = update_tracking_session(
            detection
        )

        end_stale_tracking_sessions(
            timeout_seconds=30
        )

        location = (
            TrackingLocation.objects
            .filter(
                tracking_session=session
            )
            .first()
        )

        self.assertIsNotNone(
            location
        )

        self.assertIsNotNone(
            location.exited_at
        )

        self.assertEqual(
            location.exited_at,
            old_time,
        )

    def test_stale_session_closes_camera_visit(self):
        old_time = (
            timezone.now()
            - timedelta(seconds=60)
        )

        detection = self.create_detection(
            tracking_id="102",
            occurred_at=old_time,
        )

        session = update_tracking_session(
            detection
        )

        end_stale_tracking_sessions(
            timeout_seconds=30
        )

        visit = (
            TrackingCameraVisit.objects
            .filter(
                tracking_session=session
            )
            .first()
        )

        self.assertIsNotNone(
            visit
        )

        self.assertIsNotNone(
            visit.exited_at
        )

        self.assertEqual(
            visit.exited_at,
            old_time,
        )

    def test_recent_active_session_is_not_ended(self):
        recent_time = (
            timezone.now()
            - timedelta(seconds=5)
        )

        detection = self.create_detection(
            tracking_id="103",
            occurred_at=recent_time,
        )

        session = update_tracking_session(
            detection
        )

        ended_count = end_stale_tracking_sessions(
            timeout_seconds=30
        )

        self.assertEqual(
            ended_count,
            0,
        )

        session.refresh_from_db()

        self.assertEqual(
            session.status,
            TrackingSession.Status.ACTIVE,
        )

    def test_no_stale_sessions_returns_zero(self):
        ended_count = end_stale_tracking_sessions(
            timeout_seconds=30
        )

        self.assertEqual(
            ended_count,
            0,
        )

    def test_tracking_summary_contains_complete_history(self):
        first_time = timezone.now()

        first_detection = self.create_detection(
            tracking_id="200",
            occurred_at=first_time,
            x="0.100000",
            y="0.100000",
            zone="Zone A",
        )

        session = update_tracking_session(
            first_detection
        )

        second_detection = self.create_detection(
            tracking_id="200",
            occurred_at=(
                first_time
                + timedelta(seconds=10)
            ),
            x="0.400000",
            y="0.500000",
            zone="Zone A",
        )

        update_tracking_session(
            second_detection
        )

        summary = get_tracking_session_summary(
            session
        )

        self.assertIn(
            "session",
            summary,
        )

        self.assertIn(
            "points",
            summary,
        )

        self.assertIn(
            "locations",
            summary,
        )

        self.assertIn(
            "camera_visits",
            summary,
        )

        self.assertIn(
            "identities",
            summary,
        )

        self.assertEqual(
            summary["session"]["tracking_id"],
            "200",
        )

        self.assertEqual(
            summary["session"]["object_type"],
            "PERSON",
        )

        self.assertEqual(
            summary["session"]["label"],
            "person",
        )

        self.assertEqual(
            summary["session"]["total_detections"],
            2,
        )

        self.assertEqual(
            len(summary["points"]),
            2,
        )

        self.assertEqual(
            len(summary["locations"]),
            1,
        )

        self.assertEqual(
            len(summary["camera_visits"]),
            1,
        )

        self.assertEqual(
            summary["locations"][0]["zone"],
            "Zone A",
        )

        self.assertEqual(
            summary["camera_visits"][0]["camera_id"],
            self.camera.id,
        )

        self.assertEqual(
            summary["camera_visits"][0]["detection_count"],
            2,
        )

    def test_summary_contains_distance_and_counts(self):
        first_time = timezone.now()

        first_detection = self.create_detection(
            tracking_id="201",
            occurred_at=first_time,
            x="0.100000",
            y="0.100000",
        )

        session = update_tracking_session(
            first_detection
        )

        second_detection = self.create_detection(
            tracking_id="201",
            occurred_at=(
                first_time
                + timedelta(seconds=5)
            ),
            x="0.400000",
            y="0.500000",
        )

        session = update_tracking_session(
            second_detection
        )

        summary = get_tracking_session_summary(
            session
        )

        self.assertAlmostEqual(
            float(
                summary["session"]["total_distance"]
            ),
            0.5,
            places=5,
        )

        self.assertEqual(
            summary["session"]["camera_count"],
            1,
        )

        self.assertEqual(
            summary["session"]["zone_count"],
            1,
        )

        self.assertEqual(
            summary["session"]["total_detections"],
            2,
        )
