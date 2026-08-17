from django.db import models


class StorageLocation(models.Model):
    class StorageType(models.TextChoices):
        LOCAL_FOLDER = "LOCAL_FOLDER", "Local Folder"
        NETWORK_FOLDER = "NETWORK_FOLDER", "Network Folder"
        OTHER = "OTHER", "Other"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="storage_locations",
    )

    name = models.CharField(max_length=200)

    path = models.TextField(
        help_text="User-selected folder used for recordings and generated media.",
    )

    storage_type = models.CharField(
        max_length=30,
        choices=StorageType.choices,
        default=StorageType.LOCAL_FOLDER,
    )

    enabled = models.BooleanField(default=True)

    rolling_enabled = models.BooleanField(default=True)

    max_size_gb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=6,
    )

    current_size_bytes = models.BigIntegerField(
        default=0,
    )

    delete_oldest_unprotected = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_storage_name_per_organization",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.path}"
