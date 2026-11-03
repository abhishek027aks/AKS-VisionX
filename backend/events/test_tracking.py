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


class TrackingServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Tracking Test Organization",
            slug="tracking-test-organization",
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="Tracking Test Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

    def create_detection(
        self,
        tracking_id="1",
        occurred_at=None,
        x="0.100000",
        y="0.100000",
        zone="Zone A",
        label="person",
        object_type="PERSON",
    ):
        occurred_at = (
            occurred_at
            or timezone.now()
        )

        return Detection.objects.create(
            organization=self.organization,
            camera=self.camera,
            object_type=object_type,
            label=label,
            confidence=Decimal("0.90"),
            tracking_id=tracking_id,
            status=Detection.DetectionStatus.ACTIVE,
            first_seen_at=occurred_at,
            last_seen_at=occurred_at,
            bbox_x=Decimal(x),
            bbox_y=Decimal(y),
            bbox_width=Decimal("0.20"),
            bbox_height=Decimal("0.30"),
            metadata={
                "zone": zone,
            },
        )

    def test_first_detection_creates_complete_tracking_pipeline(self):
        occurred_at = timezone.now()

        detection = self.create_detection(
            tracking_id="101",
            occurred_at=occurred_at,
            x="0.100000",
            y="0.200000",
            zone="Zone A",
        )

        session = update_tracking_session(
            detection
        )

        self.assertIsNotNone(session)

        self.assertEqual(
            TrackingSession.objects.count(),
            1,
        )

        self.assertEqual(
            TrackingPoint.objects.count(),
            1,
        )

        self.assertEqual(
            TrackingLocation.objects.count(),
            1,
        )

        self.assertEqual(
            TrackingCameraVisit.objects.count(),
            1,
        )

        session.refresh_from_db()

        self.assertEqual(
            session.tracking_id,
            "101",
        )

        self.assertEqual(
            session.object_type,
            "PERSON",
        )

        self.assertEqual(
            session.label,
            "person",
        )

        self.assertEqual(
            session.total_detections,
            1,
        )

        self.assertEqual(
            session.first_seen_x,
            Decimal("0.100000"),
        )

        self.assertEqual(
            session.first_seen_y,
            Decimal("0.200000"),
        )

        point = TrackingPoint.objects.first()

        self.assertEqual(
            point.tracking_session,
            session,
        )

        self.assertEqual(
            point.camera,
            self.camera,
        )

        self.assertEqual(
            point.zone,
            "Zone A",
        )

        self.assertEqual(
            point.x,
            Decimal("0.100000"),
        )

        location = TrackingLocation.objects.first()

        self.assertEqual(
            location.tracking_session,
            session,
        )

        self.assertEqual(
            location.camera,
            self.camera,
        )

        self.assertEqual(
            location.zone,
            "Zone A",
        )

        self.assertEqual(
            location.first_x,
            Decimal("0.100000"),
        )

        visit = TrackingCameraVisit.objects.first()

        self.assertEqual(
            visit.tracking_session,
            session,
        )

        self.assertEqual(
            visit.camera,
            self.camera,
        )

        self.assertEqual(
            visit.detection_count,
            1,
        )

    def test_same_tracking_id_reuses_active_session(self):
        first_time = timezone.now()

        first_detection = self.create_detection(
            tracking_id="200",
            occurred_at=first_time,
            x="0.100000",
            y="0.100000",
            zone="Zone A",
        )

        first_session = update_tracking_session(
            first_detection
        )

        second_detection = self.create_detection(
            tracking_id="200",
            occurred_at=first_time + timedelta(seconds=5),
            x="0.300000",
            y="0.400000",
            zone="Zone A",
        )

        second_session = update_tracking_session(
            second_detection
        )

        self.assertEqual(
            first_session.id,
            second_session.id,
        )

        self.assertEqual(
            TrackingSession.objects.count(),
            1,
        )

        second_session.refresh_from_db()

        self.assertEqual(
            second_session.total_detections,
            2,
        )

        self.assertEqual(
            second_session.last_seen_x,
            Decimal("0.300000"),
        )

        self.assertEqual(
            second_session.last_seen_y,
            Decimal("0.400000"),
        )

        self.assertEqual(
            TrackingPoint.objects.count(),
            2,
        )

        visit = TrackingCameraVisit.objects.first()

        self.assertEqual(
            visit.detection_count,
            2,
        )

    def test_movement_updates_distance(self):
        first_time = timezone.now()

        first_detection = self.create_detection(
            tracking_id="300",
            occurred_at=first_time,
            x="0.100000",
            y="0.100000",
            zone="Zone A",
        )

        session = update_tracking_session(
            first_detection
        )

        second_detection = self.create_detection(
            tracking_id="300",
            occurred_at=first_time + timedelta(seconds=2),
            x="0.400000",
            y="0.500000",
            zone="Zone A",
        )

        session = update_tracking_session(
            second_detection
        )

        session.refresh_from_db()

        expected_distance = Decimal(
            "0.5"
        )

        self.assertAlmostEqual(
            float(session.total_distance),
            float(expected_distance),
            places=5,
        )

        self.assertEqual(
            TrackingPoint.objects.count(),
            2,
        )

    def test_zone_change_closes_old_location_and_creates_new_location(
        self,
    ):
        first_time = timezone.now()

        first_detection = self.create_detection(
            tracking_id="400",
            occurred_at=first_time,
            x="0.100000",
            y="0.100000",
            zone="Zone A",
        )

        session = update_tracking_session(
            first_detection
        )

        second_detection = self.create_detection(
            tracking_id="400",
            occurred_at=first_time + timedelta(seconds=10),
            x="0.500000",
            y="0.500000",
            zone="Zone B",
        )

        update_tracking_session(
            second_detection
        )

        locations = TrackingLocation.objects.filter(
            tracking_session=session,
        ).order_by("entered_at")

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

        self.assertIsNotNone(
            first_location.exited_at,
        )

        self.assertEqual(
            first_location.duration_seconds,
            10,
        )

        self.assertEqual(
            second_location.zone,
            "Zone B",
        )

        self.assertIsNone(
            second_location.exited_at,
        )

        session.refresh_from_db()

        self.assertEqual(
            session.zone_count,
            2,
        )

    def test_tracking_without_id_does_not_create_session(self):
        detection = self.create_detection(
            tracking_id="",
        )

        session = update_tracking_session(
            detection
        )

        self.assertIsNone(
            session
        )

        self.assertEqual(
            TrackingSession.objects.count(),
            0,
        )

        self.assertEqual(
            TrackingPoint.objects.count(),
            0,
        )

        self.assertEqual(
            TrackingLocation.objects.count(),
            0,
        )

        self.assertEqual(
            TrackingCameraVisit.objects.count(),
            0,
        )

    def test_ended_session_creates_new_session(self):
        first_time = timezone.now()

        first_detection = self.create_detection(
            tracking_id="500",
            occurred_at=first_time,
        )

        first_session = update_tracking_session(
            first_detection
        )

        first_session.status = TrackingSession.Status.ENDED
        first_session.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        second_detection = self.create_detection(
            tracking_id="500",
            occurred_at=first_time + timedelta(seconds=20),
            x="0.600000",
            y="0.600000",
        )

        second_session = update_tracking_session(
            second_detection
        )

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

        self.assertEqual(
            second_session.total_detections,
            1,
        )
