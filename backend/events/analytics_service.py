from datetime import datetime, time, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone

from events.models import Detection, TrackingSession


TRACKING_PERIODS = {"daily", "weekly", "monthly"}


def _period_dates(period, today):
    if period == "daily":
        start = today
        end = today + timedelta(days=1)
    elif period == "weekly":
        start = today - timedelta(days=6)
        end = today + timedelta(days=1)
    elif period == "monthly":
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    else:
        raise ValueError("Period must be daily, weekly, or monthly.")

    return start, end


def _aware_midnight(date, tz):
    return timezone.make_aware(
        datetime.combine(date, time.min),
        timezone=tz,
    )


def _bucket_key(value, period):
    if period == "daily":
        return value.strftime("%H:00")
    if isinstance(value, datetime):
        value = value.date()
    return value.isoformat()


def get_tracking_analytics(
    tracking_sessions,
    detections,
    period="daily",
    reference_time=None,
):
    """Aggregate raw detections separately from tracked-object sessions."""
    if period not in TRACKING_PERIODS:
        raise ValueError("Period must be daily, weekly, or monthly.")

    tz = timezone.get_current_timezone()
    local_now = timezone.localtime(reference_time or timezone.now(), tz)
    start_date, end_date = _period_dates(period, local_now.date())
    start = _aware_midnight(start_date, tz)
    end = _aware_midnight(end_date, tz)

    sessions = tracking_sessions.filter(
        first_seen_at__gte=start,
        first_seen_at__lt=end,
    )
    period_detections = detections.filter(
        first_seen_at__gte=start,
        first_seen_at__lt=end,
    )

    if period == "daily":
        bucket_expression = TruncHour("first_seen_at", tzinfo=tz)
        bucket_values = [
            f"{hour:02d}:00"
            for hour in range(24)
        ]
    else:
        bucket_expression = TruncDate("first_seen_at", tzinfo=tz)
        bucket_values = []
        current_date = start_date
        while current_date < end_date:
            bucket_values.append(current_date.isoformat())
            current_date += timedelta(days=1)

    buckets = {
        value: {
            "period": value,
            "detections": 0,
            "tracked_tracks": 0,
        }
        for value in bucket_values
    }

    for row in (
        period_detections
        .annotate(bucket=bucket_expression)
        .values("bucket")
        .annotate(count=Count("id"))
        .order_by("bucket")
    ):
        key = _bucket_key(row["bucket"], period)
        if key in buckets:
            buckets[key]["detections"] = row["count"]

    for row in (
        sessions
        .annotate(bucket=bucket_expression)
        .values("bucket")
        .annotate(count=Count("id"))
        .order_by("bucket")
    ):
        key = _bucket_key(row["bucket"], period)
        if key in buckets:
            buckets[key]["tracked_tracks"] = row["count"]

    tracks_by_type = list(
        sessions
        .values("object_type")
        .annotate(count=Count("id"))
        .order_by("object_type")
    )
    detections_by_type = list(
        period_detections
        .values("object_type")
        .annotate(count=Count("id"))
        .order_by("object_type")
    )
    animal_species = list(
        sessions
        .filter(object_type=TrackingSession.ObjectType.ANIMAL)
        .values("label")
        .annotate(count=Count("id"))
        .order_by("-count", "label")
    )

    return {
        "period": period,
        "starts_at": start,
        "ends_at": end,
        "counts": {
            "detections": period_detections.count(),
            "tracked_tracks": sessions.count(),
            "tracked_tracks_by_type": tracks_by_type,
            "detections_by_type": detections_by_type,
            "animal_tracks_by_species": animal_species,
        },
        "timeline": list(buckets.values()),
        "count_semantics": (
            "Detections count frame-level records and can include repeat "
            "observations. Tracked tracks count tracker sessions that began "
            "during the selected period; they are not verified entry/exit "
            "counts or occupancy."
        ),
    }
