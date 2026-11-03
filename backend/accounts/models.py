from django.contrib.auth.models import AbstractUser
from django.db import models


class Organization(models.Model):
    """
    Represents a business, household, or deployment
    using an AKS VisionX installation.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom AKS VisionX user model.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
<<<<<<< HEAD
    google_subject = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d

    def __str__(self):
        return self.username
