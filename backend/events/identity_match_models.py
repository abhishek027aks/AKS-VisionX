from django.db import models


class IdentityMatch(models.Model):
    class IdentityType(models.TextChoices):
        PERSON = "PERSON", "Person"
        VEHICLE = "VEHICLE", "Vehicle"

    class MatchMethod(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        FACE = "FACE", "Face Recognition"
        PLATE = "PLATE", "Number Plate"
        VISUAL = "VISUAL", "Visual Match"
        UNKNOWN = "UNKNOWN", "Unknown"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="identity_matches",
    )

    tracking_session = models.ForeignKey(
        "events.TrackingSession",
        on_delete=models.CASCADE,
        related_name="identity_matches",
    )

    person_profile = models.ForeignKey(
        "events.PersonProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="identity_matches",
    )

    vehicle_profile = models.ForeignKey(
        "events.VehicleProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="identity_matches",
    )

    identity_type = models.CharField(
        max_length=20,
        choices=IdentityType.choices,
    )

    match_method = models.CharField(
        max_length=20,
        choices=MatchMethod.choices,
        default=MatchMethod.UNKNOWN,
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    matched_at = models.DateTimeField()

    is_confirmed = models.BooleanField(
        default=False,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-matched_at"]
        indexes = [
            models.Index(
                fields=["organization", "-matched_at"],
                name="identity_org_time_idx",
            ),
            models.Index(
                fields=["tracking_session", "-matched_at"],
                name="identity_track_time_idx",
            ),
            models.Index(
                fields=["identity_type", "-matched_at"],
                name="identity_type_time_idx",
            ),
        ]

    def __str__(self):
        if self.person_profile_id:
            return f"{self.person_profile.name} - {self.tracking_session.tracking_id}"

        if self.vehicle_profile_id:
            return f"{self.vehicle_profile.name} - {self.tracking_session.tracking_id}"

        return self.tracking_session.tracking_id
