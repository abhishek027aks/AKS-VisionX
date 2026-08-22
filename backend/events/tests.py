from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import Organization
from cameras.models import Camera

from events.models import (
    Detection,
    TrackingSession,
    TrackingPoint,
    TrackingLocation,
    TrackingCameraVisit,
)

from events.tracking_service import update_tracking_session
from events.tracking_end_service import end_stale_tracking_sessions


class TrackingPipelineTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Tracking Test Organization",
            slug="tracking-test-organization",
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="Test Camera",
            connection_type=Camera.ConnectionType.RTSP,
        )

    def create_detection(
        self,
        tracking_id="person-1",
        occurred_at=None,
        x="0.100000",
        y="0.100000",
        zone="Zone A",
        label="person",
    ):
        occurred_at = occurred_at or timezone.now()

        return Detection.objects.create(
            organization=self.organization,
            camera=self.camera,
            object_type=Detection.ObjectType.PERSON,
            label=label,
            confidence=Decimal("0.95"),
            tracking_id=tracking_id,
            status=Detection.DetectionStatus.ACTIVE,
            first_seen_at=occurred_at,
            last_seen_at=occurred_at,
            bbox_x=Decimal(x),
            bbox_y=Decimal(y),
            bbox_width=Decimal("0.100000"),
            bbox_height=Decimal("0.200000"),
            metadata={
                "zone": zone,
            },
        )

    def test_first_detection_creates_tracking_session(self):
        detection = self.create_detection()

        session = update_tracking_session(detection)

        self.assertIsNotNone(session)
        self.assertEqual(
            TrackingSession.objects.count(),
            1,
        )
        self.assertEqual(
            session.tracking_id,
            "person-1",
        )
        self.assertEqual(
            session.status,
            TrackingSession.Status.ACTIVE,
        )
        self.assertEqual(
            session.total_detections,
            1,
        )

    def test_detection_creates_tracking_point(self):
        detection = self.create_detection()

        session = update_tracking_session(detection)

        self.assertEqual(
            TrackingPoint.objects.filter(
                tracking_session=session
            ).count(),
            1,
        )

        point = TrackingPoint.objects.get(
            tracking_session=session
        )

        self.assertEqual(point.x, Decimal("0.100000"))
        self.assertEqual(point.y, Decimal("0.100000"))
        self.assertEqual(point.zone, "Zone A")

    def test_second_detection_updates_same_session(self):
        first_time = timezone.now()

        first = self.create_detection(
            occurred_at=first_time,
            x="0.100000",
            y="0.100000",
        )

        session1 = update_tracking_session(first)

        second = self.create_detection(
            occurred_at=first_time + timedelta(seconds=5),
            x="0.200000",
            y="0.200000",
        )

        session2 = update_tracking_session(second)

        self.assertEqual(
            session1.id,
            session2.id,
        )

        self.assertEqual(
            TrackingSession.objects.count(),
            1,
        )

        self.assertEqual(
            session2.total_detections,
            2,
        )

        self.assertEqual(
            session2.last_seen_x,
            Decimal("0.200000"),
        )

        self.assertEqual(
            TrackingPoint.objects.filter(
                tracking_session=session2
            ).count(),
            2,
        )

    def test_location_is_created_and_updated(self):
        first_time = timezone.now()

        first = self.create_detection(
            occurred_at=first_time,
            zone="Zone A",
        )

        session = update_tracking_session(first)

        self.assertEqual(
            TrackingLocation.objects.filter(
                tracking_session=session
            ).count(),
            1,
        )

        second = self.create_detection(
            occurred_at=first_time + timedelta(seconds=10),
            zone="Zone A",
        )

        update_tracking_session(second)

        self.assertEqual(
            TrackingLocation.objects.filter(
                tracking_session=session
            ).count(),
            1,
        )

        location = TrackingLocation.objects.get(
            tracking_session=session
        )

        self.assertEqual(
            location.zone,
            "Zone A",
        )

        self.assertEqual(
            location.duration_seconds,
            10,
        )

    def test_zone_change_creates_new_location(self):
        first_time = timezone.now()

        first = self.create_detection(
            occurred_at=first_time,
            zone="Zone A",
        )

        session = update_tracking_session(first)

        second = self.create_detection(
            occurred_at=first_time + timedelta(seconds=10),
            zone="Zone B",
        )

        update_tracking_session(second)

        locations = TrackingLocation.objects.filter(
            tracking_session=session
        ).order_by("entered_at", "id")

        self.assertEqual(
            locations.count(),
            2,
        )

        first_location = locations[0]
        second_location = locations[1]

        self.assertEqual(
            first_location.zone,
            "Zone A",
        )

        self.assertEqual(
            second_location.zone,
            "Zone B",
        )

        self.assertIsNotNone(
            first_location.exited_at
        )

    def test_camera_visit_is_created(self):
        detection = self.create_detection()

        session = update_tracking_session(detection)

        visits = TrackingCameraVisit.objects.filter(
            tracking_session=session
        )

        self.assertEqual(
            visits.count(),
            1,
        )

        visit = visits.first()

        self.assertEqual(
            visit.camera_id,
            self.camera.id,
        )

        self.assertEqual(
            visit.detection_count,
            1,
        )

    def test_distance_is_calculated(self):
        first_time = timezone.now()

        first = self.create_detection(
            occurred_at=first_time,
            x="0.100000",
            y="0.100000",
        )

        session = update_tracking_session(first)

        second = self.create_detection(
            occurred_at=first_time + timedelta(seconds=5),
            x="0.400000",
            y="0.500000",
        )

        session = update_tracking_session(second)

        expected = Decimal("0.5")

        self.assertAlmostEqual(
            float(session.total_distance),
            float(expected),
            places=5,
        )

    def test_stale_session_is_ended(self):
        old_time = timezone.now() - timedelta(
            seconds=60
        )

        detection = self.create_detection(
            occurred_at=old_time,
        )

        session = update_tracking_session(detection)

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

        location = TrackingLocation.objects.get(
            tracking_session=session
        )

        self.assertIsNotNone(
            location.exited_at,
        )

        visit = TrackingCameraVisit.objects.get(
            tracking_session=session
        )

        self.assertIsNotNone(
            visit.exited_at,
        )

    def test_new_session_is_created_after_previous_session_ended(self):
        old_time = timezone.now() - timedelta(
            seconds=60
        )

        first = self.create_detection(
            tracking_id="person-1",
            occurred_at=old_time,
        )

        first_session = update_tracking_session(first)

        end_stale_tracking_sessions(
            timeout_seconds=30
        )

        first_session.refresh_from_db()

        self.assertEqual(
            first_session.status,
            TrackingSession.Status.ENDED,
        )

        new_time = timezone.now()

        second = self.create_detection(
            tracking_id="person-1",
            occurred_at=new_time,
            x="0.500000",
            y="0.500000",
        )

        second_session = update_tracking_session(second)

        self.assertNotEqual(
            first_session.id,
            second_session.id,
        )

        self.assertEqual(
            TrackingSession.objects.count(),
            2,
        )

        self.assertEqual(
            second_session.status,
            TrackingSession.Status.ACTIVE,
        )

    def test_session_summary_counts_locations_and_cameras(self):
        first_time = timezone.now()

        first = self.create_detection(
            occurred_at=first_time,
            zone="Zone A",
        )

        session = update_tracking_session(first)

        second = self.create_detection(
            occurred_at=first_time + timedelta(seconds=5),
            zone="Zone B",
        )

        session = update_tracking_session(second)

        session.refresh_from_db()

        self.assertEqual(
            session.zone_count,
            2,
        )

        self.assertEqual(
            session.camera_count,
            1,
        )


