from events.models import (
    IdentityMatch,
    TrackingCameraVisit,
    TrackingLocation,
    TrackingPoint,
    TrackingSession,
)


def get_tracking_session_summary(session):
    """
    Return a complete tracking history summary.
    """

    points = (
        TrackingPoint.objects
        .filter(tracking_session=session)
        .select_related("camera")
        .order_by("occurred_at", "id")
    )

    locations = (
        TrackingLocation.objects
        .filter(tracking_session=session)
        .select_related("camera")
        .order_by("entered_at", "id")
    )

    camera_visits = (
        TrackingCameraVisit.objects
        .filter(tracking_session=session)
        .select_related("camera")
        .order_by("entered_at", "id")
    )

    identity_matches = (
        IdentityMatch.objects
        .filter(tracking_session=session)
        .select_related(
            "person_profile",
            "vehicle_profile",
        )
        .order_by("-matched_at", "-id")
    )

    return {
        "session": {
            "id": session.id,
            "tracking_id": session.tracking_id,
            "object_type": session.object_type,
            "label": session.label,
            "status": session.status,
            "first_seen_at": session.first_seen_at,
            "last_seen_at": session.last_seen_at,
            "duration_seconds": session.duration_seconds,
            "total_detections": session.total_detections,
            "total_distance": session.total_distance,
            "camera_count": session.camera_count,
            "zone_count": session.zone_count,
        },

        "points": [
            {
                "id": point.id,
                "camera_id": point.camera_id,
                "camera": point.camera.name,
                "occurred_at": point.occurred_at,
                "x": point.x,
                "y": point.y,
                "width": point.width,
                "height": point.height,
                "confidence": point.confidence,
                "zone": point.zone,
                "metadata": point.metadata,
            }
            for point in points
        ],

        "locations": [
            {
                "id": location.id,
                "camera_id": location.camera_id,
                "camera": location.camera.name,
                "zone": location.zone,
                "entered_at": location.entered_at,
                "exited_at": location.exited_at,
                "duration_seconds": location.duration_seconds,
                "first_x": location.first_x,
                "first_y": location.first_y,
                "last_x": location.last_x,
                "last_y": location.last_y,
            }
            for location in locations
        ],

        "camera_visits": [
            {
                "id": visit.id,
                "camera_id": visit.camera_id,
                "camera": visit.camera.name,
                "entered_at": visit.entered_at,
                "exited_at": visit.exited_at,
                "duration_seconds": visit.duration_seconds,
                "first_x": visit.first_x,
                "first_y": visit.first_y,
                "last_x": visit.last_x,
                "last_y": visit.last_y,
                "detection_count": visit.detection_count,
                "metadata": visit.metadata,
            }
            for visit in camera_visits
        ],

        "identities": [
            {
                "id": match.id,
                "identity_type": match.identity_type,
                "match_method": match.match_method,
                "confidence": match.confidence,
                "matched_at": match.matched_at,
                "is_confirmed": match.is_confirmed,
                "person": (
                    match.person_profile.name
                    if match.person_profile_id
                    else None
                ),
                "vehicle": (
                    match.vehicle_profile.name
                    if match.vehicle_profile_id
                    else None
                ),
                "metadata": match.metadata,
            }
            for match in identity_matches
        ],
    }
