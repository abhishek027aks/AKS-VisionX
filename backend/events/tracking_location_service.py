from django.utils import timezone

from events.models import TrackingLocation


def update_tracking_location(
    tracking_session,
    camera,
    occurred_at,
    zone="",
    x=None,
    y=None,
):
    """
    Create or update the current location of a tracking session.

    A new location record is created whenever the tracked object
    changes zone or camera.
    """

    zone = zone or ""

    current = (
        TrackingLocation.objects
        .filter(
            tracking_session=tracking_session,
            exited_at__isnull=True,
        )
        .order_by("-entered_at", "-id")
        .first()
    )

    if current is None:
        return TrackingLocation.objects.create(
            tracking_session=tracking_session,
            camera=camera,
            zone=zone,
            entered_at=occurred_at,
            first_x=x,
            first_y=y,
            last_x=x,
            last_y=y,
        )

    same_location = (
        current.camera_id == camera.id
        and current.zone == zone
    )

    if same_location:
        current.last_x = x
        current.last_y = y
        current.duration_seconds = max(
            0,
            int(
                (
                    occurred_at - current.entered_at
                ).total_seconds()
            ),
        )
        current.save(
            update_fields=[
                "last_x",
                "last_y",
                "duration_seconds",
                "updated_at",
            ]
        )
        return current

    current.exited_at = occurred_at
    current.duration_seconds = max(
        0,
        int(
            (
                occurred_at - current.entered_at
            ).total_seconds()
        ),
    )
    current.save(
        update_fields=[
            "exited_at",
            "duration_seconds",
            "updated_at",
        ]
    )

    return TrackingLocation.objects.create(
        tracking_session=tracking_session,
        camera=camera,
        zone=zone,
        entered_at=occurred_at,
        first_x=x,
        first_y=y,
        last_x=x,
        last_y=y,
    )


def refresh_tracking_location_summary(tracking_session):
    """
    Refresh zone and camera counts for a tracking session.
    """

    locations = TrackingLocation.objects.filter(
        tracking_session=tracking_session,
    )

    zone_count = (
        locations
        .exclude(zone="")
        .values("zone")
        .distinct()
        .count()
    )

    camera_count = (
        locations
        .values("camera_id")
        .distinct()
        .count()
    )

    tracking_session.zone_count = zone_count
    tracking_session.camera_count = max(
        1,
        camera_count,
    )

    tracking_session.save(
        update_fields=[
            "zone_count",
            "camera_count",
            "updated_at",
        ]
    )

    return tracking_session
