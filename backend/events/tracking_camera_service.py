from events.models import TrackingCameraVisit


def update_tracking_camera_visit(
    tracking_session,
    camera,
    occurred_at,
    x=None,
    y=None,
):
    """
    Create or update the current camera visit for a tracking session.

    A new visit is created whenever the tracked object
    appears in a different camera.
    """

    current = (
        TrackingCameraVisit.objects
        .filter(
            tracking_session=tracking_session,
            exited_at__isnull=True,
        )
        .order_by("-entered_at", "-id")
        .first()
    )

    if current is None:
        return TrackingCameraVisit.objects.create(
            tracking_session=tracking_session,
            camera=camera,
            entered_at=occurred_at,
            first_x=x,
            first_y=y,
            last_x=x,
            last_y=y,
            detection_count=1,
        )

    if current.camera_id == camera.id:
        current.last_x = x
        current.last_y = y
        current.detection_count += 1
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
                "detection_count",
                "duration_seconds",
                "updated_at",
            ]
        )

        return current

    # Object moved to another camera.
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

    return TrackingCameraVisit.objects.create(
        tracking_session=tracking_session,
        camera=camera,
        entered_at=occurred_at,
        first_x=x,
        first_y=y,
        last_x=x,
        last_y=y,
        detection_count=1,
    )


def close_tracking_camera_visit(
    tracking_session,
    occurred_at,
):
    """
    Close the currently active camera visit.
    """

    current = (
        TrackingCameraVisit.objects
        .filter(
            tracking_session=tracking_session,
            exited_at__isnull=True,
        )
        .order_by("-entered_at", "-id")
        .first()
    )

    if current is None:
        return None

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

    return current
