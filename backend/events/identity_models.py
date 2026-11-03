from django.db import models


class PersonProfile(models.Model):
    class Category(models.TextChoices):
        FAMILY = "FAMILY", "Family"
        EMPLOYEE = "EMPLOYEE", "Employee"
        VISITOR = "VISITOR", "Visitor"
        OTHER = "OTHER", "Other"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="person_profiles",
    )

    name = models.CharField(max_length=200)

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )

    is_known = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True)

    # Reserved for future local face-recognition/embedding system.
    recognition_metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_person_profile_per_org",
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "category"],
                name="person_org_category_idx",
            ),
            models.Index(
                fields=["organization", "is_known"],
                name="person_org_known_idx",
            ),
        ]

    def __str__(self):
        return self.name


class VehicleProfile(models.Model):
    class Category(models.TextChoices):
        PERSONAL = "PERSONAL", "Personal"
        FAMILY = "FAMILY", "Family"
        EMPLOYEE = "EMPLOYEE", "Employee"
        VISITOR = "VISITOR", "Visitor"
        OTHER = "OTHER", "Other"

    class VehicleType(models.TextChoices):
        CAR = "CAR", "Car"
        MOTORCYCLE = "MOTORCYCLE", "Motorcycle"
        SCOOTER = "SCOOTER", "Scooter"
        TRUCK = "TRUCK", "Truck"
        BUS = "BUS", "Bus"
        OTHER = "OTHER", "Other"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="vehicle_profiles",
    )

    name = models.CharField(max_length=200)

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )

    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.CAR,
    )

    registration_number = models.CharField(
        max_length=50,
        blank=True,
    )

    is_known = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True)

    recognition_metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_vehicle_profile_per_org",
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "category"],
                name="vehicle_org_category_idx",
            ),
            models.Index(
                fields=["organization", "registration_number"],
                name="vehicle_org_reg_idx",
            ),
        ]

    def __str__(self):
        return self.name
