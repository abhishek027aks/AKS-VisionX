from __future__ import annotations

from typing import Any

from django.utils import timezone


class PTZError(Exception):
    pass


class ONVIFPTZService:
    """
    Small ONVIF PTZ adapter.

    Uses the camera host/port/username/password already stored
    on the Camera model.
    """

    def __init__(self, camera):
        self.camera = camera
        self.client = None
        self.media = None
        self.ptz = None
        self.profile = None

    def connect(self):
        try:
            from onvif import ONVIFCamera
        except Exception as exc:
            raise PTZError(
                "ONVIF package is not available."
            ) from exc

        host = (self.camera.host or "").strip()

        if not host:
            raise PTZError(
                "Camera host is not configured."
            )

        port = int(self.camera.port or 80)

        username = self.camera.username or ""
        password = self.camera.get_credential() or ""

        self.client = ONVIFCamera(
            host,
            port,
            username,
            password,
        )

        self.media = self.client.create_media_service()
        self.ptz = self.client.create_ptz_service()

        profiles = self.media.GetProfiles()

        if not profiles:
            raise PTZError(
                "Camera returned no ONVIF media profiles."
            )

        # Prefer a profile containing a PTZ configuration.
        selected = None

        for profile in profiles:
            if getattr(
                profile,
                "PTZConfiguration",
                None,
            ) is not None:
                selected = profile
                break

        self.profile = selected or profiles[0]

        if getattr(
            self.profile,
            "PTZConfiguration",
            None,
        ) is None:
            raise PTZError(
                "This camera does not expose ONVIF PTZ."
            )

        return self

    def _ensure_connected(self):
        if self.ptz is None or self.profile is None:
            self.connect()

    def get_status(self) -> dict[str, Any]:
        self._ensure_connected()

        try:
            response = self.ptz.GetStatus(
                {
                    "ProfileToken": self.profile.token,
                }
            )
        except Exception as exc:
            raise PTZError(
                "Unable to read PTZ status."
            ) from exc

        position = getattr(
            response,
            "Position",
            None,
        )

        pan_tilt = getattr(
            position,
            "PanTilt",
            None,
        )

        zoom = getattr(
            position,
            "Zoom",
            None,
        )

        return {
            "camera_id": self.camera.id,
            "supported": True,
            "timestamp": timezone.now(),
            "pan": (
                float(pan_tilt.x)
                if pan_tilt is not None
                and getattr(pan_tilt, "x", None) is not None
                else None
            ),
            "tilt": (
                float(pan_tilt.y)
                if pan_tilt is not None
                and getattr(pan_tilt, "y", None) is not None
                else None
            ),
            "zoom": (
                float(zoom.x)
                if zoom is not None
                and getattr(zoom, "x", None) is not None
                else None
            ),
        }

    def continuous_move(
        self,
        pan: float = 0.0,
        tilt: float = 0.0,
        zoom: float = 0.0,
        timeout_seconds: float = 1.0,
    ):
        self._ensure_connected()

        request = self.ptz.create_type(
            "ContinuousMove"
        )

        request.ProfileToken = self.profile.token

        velocity = request.Velocity

        if getattr(
            velocity,
            "PanTilt",
            None,
        ) is not None:
            velocity.PanTilt.x = float(pan)
            velocity.PanTilt.y = float(tilt)

        if getattr(
            velocity,
            "Zoom",
            None,
        ) is not None:
            velocity.Zoom.x = float(zoom)

        timeout = max(
            float(timeout_seconds),
            0.1,
        )

        try:
            request.Timeout = f"PT{timeout:.2f}S"
        except Exception:
            pass

        try:
            self.ptz.ContinuousMove(request)
        except Exception as exc:
            raise PTZError(
                "PTZ movement command failed."
            ) from exc

        return {
            "status": "moving",
            "pan": float(pan),
            "tilt": float(tilt),
            "zoom": float(zoom),
        }

    def stop(self):
        self._ensure_connected()

        request = self.ptz.create_type("Stop")
        request.ProfileToken = self.profile.token
        request.PanTilt = True
        request.Zoom = True

        try:
            self.ptz.Stop(request)
        except Exception as exc:
            raise PTZError(
                "Unable to stop PTZ movement."
            ) from exc

        return {
            "status": "stopped",
        }

    def goto_home(self):
        self._ensure_connected()

        request = self.ptz.create_type(
            "GotoHomePosition"
        )

        request.ProfileToken = self.profile.token

        try:
            self.ptz.GotoHomePosition(request)
        except Exception as exc:
            raise PTZError(
                "Unable to move camera to home position."
            ) from exc

        return {
            "status": "home",
        }

    def get_presets(self):
        self._ensure_connected()

        try:
            presets = self.ptz.GetPresets(
                {
                    "ProfileToken": self.profile.token,
                }
            )
        except Exception as exc:
            raise PTZError(
                "Unable to read PTZ presets."
            ) from exc

        result = []

        for preset in presets or []:
            result.append(
                {
                    "token": str(
                        getattr(
                            preset,
                            "token",
                            "",
                        )
                    ),
                    "name": str(
                        getattr(
                            preset,
                            "Name",
                            "",
                        )
                        or ""
                    ),
                }
            )

        return result

    def goto_preset(self, token: str):
        self._ensure_connected()

        request = self.ptz.create_type(
            "GotoPreset"
        )

        request.ProfileToken = self.profile.token
        request.PresetToken = str(token)

        try:
            self.ptz.GotoPreset(request)
        except Exception as exc:
            raise PTZError(
                "Unable to move camera to preset."
            ) from exc

        return {
            "status": "preset",
            "token": str(token),
        }


def detect_ptz(camera):
    """
    Probe ONVIF PTZ support and update camera flags.
    """

    try:
        service = ONVIFPTZService(camera)
        service.connect()

        camera.onvif_supported = True
        camera.ptz_supported = True
        camera.save(
            update_fields=[
                "onvif_supported",
                "ptz_supported",
                "updated_at",
            ]
        )

        return {
            "onvif_supported": True,
            "ptz_supported": True,
        }

    except Exception:
        camera.onvif_supported = False
        camera.ptz_supported = False

        camera.save(
            update_fields=[
                "onvif_supported",
                "ptz_supported",
                "updated_at",
            ]
        )

        return {
            "onvif_supported": False,
            "ptz_supported": False,
        }
