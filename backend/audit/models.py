from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        PASSWORD_CHANGED = "PASSWORD_CHANGED", "Password Changed"

        CAMERA_ADDED = "CAMERA_ADDED", "Camera Added"
        CAMERA_UPDATED = "CAMERA_UPDATED", "Camera Updated"
        CAMERA_DELETED = "CAMERA_DELETED", "Camera Deleted"

        RECORDING_PROTECTED = "RECORDING_PROTECTED", "Recording Protected"
        RECORDING_UNPROTECTED = "RECORDING_UNPROTECTED", "Recording Unprotected"
        RECORDING_DELETED = "RECORDING_DELETED", "Recording Deleted"

        STORAGE_ADDED = "STORAGE_ADDED", "Storage Added"
        STORAGE_UPDATED = "STORAGE_UPDATED", "Storage Updated"
        STORAGE_DELETED = "STORAGE_DELETED", "Storage Deleted"

        EVENT_ACKNOWLEDGED = "EVENT_ACKNOWLEDGED", "Event Acknowledged"
        ALERT_ACKNOWLEDGED = "ALERT_ACKNOWLEDGED", "Alert Acknowledged"
        ALERT_RESOLVED = "ALERT_RESOLVED", "Alert Resolved"

        SETTINGS_CHANGED = "SETTINGS_CHANGED", "Settings Changed"
        PERMISSION_CHANGED = "PERMISSION_CHANGED", "Permission Changed"

        LICENSE_CREATED = "LICENSE_CREATED", "License Created"
        LICENSE_UPDATED = "LICENSE_UPDATED", "License Updated"
        LICENSE_REVOKED = "LICENSE_REVOKED", "License Revoked"

        SECURITY_ACTION = "SECURITY_ACTION", "Security Action"
        OTHER = "OTHER", "Other"

    class Result(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"
        DENIED = "DENIED", "Denied"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=40,
        choices=Action.choices,
    )

    result = models.CharField(
        max_length=20,
        choices=Result.choices,
        default=Result.SUCCESS,
    )

    description = models.TextField(
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    user_agent = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="audit_org_time_idx",
            ),
            models.Index(
                fields=["user", "-created_at"],
                name="audit_user_time_idx",
            ),
            models.Index(
                fields=["action", "-created_at"],
                name="audit_action_time_idx",
            ),
            models.Index(
                fields=["result", "-created_at"],
                name="audit_result_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.action} - {self.created_at}"

