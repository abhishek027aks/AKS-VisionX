from datetime import timedelta

from django.utils import timezone

from events.models import TrackingSession

from events.tracking_camera_service import (
    close_tracking_camera_visit,
)

from events.tracking_distance_service import (
    calculate_tracking_distance,
)

from events.tracking_location_service import (
    refresh_tracking_location_summary,
)

from events.models import TrackingLocation


def end_stale_tracking_sessions(timeout_seconds=30):
    """
    End active tracking sessions that have not received
    a detection within the configured timeout.

    Also closes the active location and camera visit.
    """

    cutoff = timezone.now() - timedelta(
        seconds=timeout_seconds
    )

    sessions = list(
        TrackingSession.objects.filter(
            status=TrackingSession.Status.ACTIVE,
            last_seen_at__lt=cutoff,
        )
    )

    ended_count = 0

    for session in sessions:
        end_time = session.last_seen_at

        active_location = (
            TrackingLocation.objects
            .filter(
                tracking_session=session,
                exited_at__isnull=True,
            )
            .order_by("-entered_at", "-id")
            .first()
        )

        if active_location is not None:
            active_location.exited_at = end_time
            active_location.duration_seconds = max(
                0,
                int(
                    (
                        end_time
                        - active_location.entered_at
                    ).total_seconds()
                ),
            )
            active_location.save(
                update_fields=[
                    "exited_at",
                    "duration_seconds",
                    "updated_at",
                ]
            )

        close_tracking_camera_visit(
            tracking_session=session,
            occurred_at=end_time,
        )

        calculate_tracking_distance(session)

        session.status = TrackingSession.Status.ENDED

        session.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        refresh_tracking_location_summary(session)

        ended_count += 1

    return ended_count
