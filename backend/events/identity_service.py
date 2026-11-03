from django.utils import timezone

from events.models import (
    IdentityMatch,
    PersonProfile,
    TrackingSession,
    VehicleProfile,
)


def link_person_identity(
    tracking_session,
    person_profile,
    match_method=IdentityMatch.MatchMethod.MANUAL,
    confidence=None,
    confirmed=True,
    metadata=None,
):
    """
    Link a tracking session to a known person profile.
    """

    if tracking_session.organization_id != person_profile.organization_id:
        raise ValueError(
            "Tracking session and person profile belong to different organizations."
        )

    match = IdentityMatch.objects.create(
        organization=tracking_session.organization,
        tracking_session=tracking_session,
        person_profile=person_profile,
        identity_type=IdentityMatch.IdentityType.PERSON,
        match_method=match_method,
        confidence=confidence,
        matched_at=timezone.now(),
        is_confirmed=confirmed,
        metadata=metadata or {},
    )

    tracking_session.person_profile = person_profile
    tracking_session.label = person_profile.name
    tracking_session.save(
        update_fields=[
            "person_profile",
            "label",
            "updated_at",
        ]
    )

    return match


def link_vehicle_identity(
    tracking_session,
    vehicle_profile,
    match_method=IdentityMatch.MatchMethod.MANUAL,
    confidence=None,
    confirmed=True,
    metadata=None,
):
    """
    Link a tracking session to a known vehicle profile.
    """

    if tracking_session.organization_id != vehicle_profile.organization_id:
        raise ValueError(
            "Tracking session and vehicle profile belong to different organizations."
        )

    match = IdentityMatch.objects.create(
        organization=tracking_session.organization,
        tracking_session=tracking_session,
        vehicle_profile=vehicle_profile,
        identity_type=IdentityMatch.IdentityType.VEHICLE,
        match_method=match_method,
        confidence=confidence,
        matched_at=timezone.now(),
        is_confirmed=confirmed,
        metadata=metadata or {},
    )

    tracking_session.vehicle_profile = vehicle_profile
    tracking_session.label = vehicle_profile.name
    tracking_session.save(
        update_fields=[
            "vehicle_profile",
            "label",
            "updated_at",
        ]
    )

    return match
