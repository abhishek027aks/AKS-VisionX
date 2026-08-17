from events.models import Detection, TrackingPoint, TrackingSession

from events.tracking_camera_service import (
    update_tracking_camera_visit,
)

from events.tracking_distance_service import (
    calculate_tracking_distance,
)

from events.tracking_location_service import (
    refresh_tracking_location_summary,
    update_tracking_location,
)


def update_tracking_session(detection):
    """
    Process one detection through the complete tracking pipeline.

    A new TrackingSession is created when the latest session
    for the same tracking identity has already ended.

    Pipeline:
        Detection
            -> TrackingSession
            -> TrackingPoint
            -> TrackingLocation
            -> CameraVisit
            -> Distance
            -> Session summary
    """

    if not detection.tracking_id:
        return None

    latest_session = (
        TrackingSession.objects
        .filter(
            organization=detection.organization,
            camera=detection.camera,
            object_type=detection.object_type,
            tracking_id=detection.tracking_id,
        )
        .order_by("-created_at", "-id")
        .first()
    )

    if (
        latest_session is not None
        and latest_session.status == TrackingSession.Status.ACTIVE
    ):
        session = latest_session
        created = False
    else:
        session = TrackingSession.objects.create(
            organization=detection.organization,
            camera=detection.camera,
            object_type=detection.object_type,
            tracking_id=detection.tracking_id,
            status=TrackingSession.Status.ACTIVE,
            first_seen_at=detection.first_seen_at,
            last_seen_at=detection.last_seen_at,
            label=detection.label,
            total_detections=1,
            first_seen_x=detection.bbox_x,
            first_seen_y=detection.bbox_y,
            last_seen_x=detection.bbox_x,
            last_seen_y=detection.bbox_y,
        )
        created = True

    if not created:
        session.last_seen_at = detection.last_seen_at
        session.last_seen_x = detection.bbox_x
        session.last_seen_y = detection.bbox_y
        session.total_detections += 1

        if detection.label:
            session.label = detection.label

        session.save(
            update_fields=[
                "last_seen_at",
                "last_seen_x",
                "last_seen_y",
                "total_detections",
                "label",
                "updated_at",
            ]
        )

    TrackingPoint.objects.create(
        tracking_session=session,
        camera=detection.camera,
        occurred_at=detection.last_seen_at,
        x=detection.bbox_x,
        y=detection.bbox_y,
        width=detection.bbox_width,
        height=detection.bbox_height,
        confidence=detection.confidence,
        zone=detection.metadata.get("zone", ""),
        metadata=detection.metadata,
    )

    update_tracking_location(
        tracking_session=session,
        camera=detection.camera,
        occurred_at=detection.last_seen_at,
        zone=detection.metadata.get("zone", ""),
        x=detection.bbox_x,
        y=detection.bbox_y,
    )

    update_tracking_camera_visit(
        tracking_session=session,
        camera=detection.camera,
        occurred_at=detection.last_seen_at,
        x=detection.bbox_x,
        y=detection.bbox_y,
    )

    calculate_tracking_distance(session)

    refresh_tracking_location_summary(session)

    session.refresh_from_db()

    return session
