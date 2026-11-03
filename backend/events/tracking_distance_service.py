from decimal import Decimal
from math import sqrt

from events.models import TrackingPoint, TrackingSession


def calculate_tracking_distance(session):
    """
    Calculate total normalized movement distance from tracking points.
    """

    points = list(
        TrackingPoint.objects
        .filter(tracking_session=session)
        .exclude(x__isnull=True, y__isnull=True)
        .order_by("occurred_at", "id")
    )

    if len(points) < 2:
        session.total_distance = Decimal("0")
        session.save(update_fields=["total_distance", "updated_at"])
        return Decimal("0")

    total = Decimal("0")

    previous = points[0]

    for current in points[1:]:
        dx = Decimal(current.x) - Decimal(previous.x)
        dy = Decimal(current.y) - Decimal(previous.y)

        distance = Decimal(
            str(sqrt(float((dx * dx) + (dy * dy))))
        )

        total += distance
        previous = current

    session.total_distance = total
    session.save(update_fields=["total_distance", "updated_at"])

    return total
