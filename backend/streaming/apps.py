import sys
import threading
import time

from django.apps import AppConfig


class StreamingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "streaming"

    def ready(self):
        # Only auto-start camera workers when Django is being
        # launched with runserver. Do not start cameras from
        # shell/tests/migrations.
        if "runserver" not in sys.argv:
            return

        if getattr(self, "_camera_bootstrap_started", False):
            return

        self._camera_bootstrap_started = True

        def bootstrap():
            time.sleep(3)

            try:
                from cameras.models import Camera
                from streaming.camera_monitor_manager import (
                    camera_monitor_manager,
                )

                cameras = (
                    Camera.objects
                    .filter(enabled=True)
                    .order_by("id")
                )

                for camera in cameras:
                    try:
                        started = (
                            camera_monitor_manager
                            .start_camera(camera.id)
                        )

                        print(
                            f"[AUTO-START] "
                            f"Camera {camera.id} "
                            f"{camera.name}: "
                            f"{'STARTED' if started else 'ALREADY RUNNING'}",
                            flush=True,
                        )

                    except Exception as exc:
                        print(
                            f"[AUTO-START] "
                            f"Camera {camera.id} failed: "
                            f"{exc!r}",
                            flush=True,
                        )

            except Exception as exc:
                print(
                    f"[AUTO-START] Bootstrap failed: {exc!r}",
                    flush=True,
                )

        threading.Thread(
            target=bootstrap,
            daemon=True,
            name="camera-auto-start",
        ).start()
