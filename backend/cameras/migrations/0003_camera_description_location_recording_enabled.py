from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cameras", "0002_rename_credential_camera_credential_encrypted"),
    ]

    operations = [
        migrations.AddField(
            model_name="camera",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="camera",
            name="location",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="camera",
            name="recording_enabled",
            field=models.BooleanField(default=True),
        ),
    ]
