import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class FramePacket:
    sequence: int
    jpeg: bytes
    timestamp: float
    width: int
    height: int


class CameraFrameHub:
    """
    Process-local latest-frame hub.

    The camera monitor owns the RTSP connection.
    Live HTTP clients only consume the latest encoded JPEG.
    """

    def __init__(
        self,
        jpeg_quality=72,
        max_width=1280,
    ):
        self.jpeg_quality = int(jpeg_quality)
        self.max_width = int(max_width)

        self._frames = {}
        self._conditions = {}
        self._lock = threading.RLock()

    def _get_condition(self, camera_id):
        with self._lock:
            condition = self._conditions.get(camera_id)

            if condition is None:
                condition = threading.Condition(
                    self._lock
                )
                self._conditions[camera_id] = condition

            return condition

    def publish(self, camera_id, frame):
        if frame is None:
            return False

        import cv2

        image = frame

        height, width = image.shape[:2]

        if width > self.max_width:
            scale = (
                self.max_width
                / float(width)
            )

            new_width = self.max_width
            new_height = max(
                1,
                int(height * scale),
            )

            image = cv2.resize(
                image,
                (
                    new_width,
                    new_height,
                ),
                interpolation=cv2.INTER_AREA,
            )

        ok, encoded = cv2.imencode(
            ".jpg",
            image,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                self.jpeg_quality,
            ],
        )

        if not ok:
            return False

        jpeg = encoded.tobytes()
        live_height, live_width = image.shape[:2]

        with self._lock:
            previous = self._frames.get(camera_id)

            sequence = (
                previous.sequence + 1
                if previous is not None
                else 1
            )

            self._frames[camera_id] = FramePacket(
                sequence=sequence,
                jpeg=jpeg,
                timestamp=time.time(),
                width=live_width,
                height=live_height,
            )

            condition = self._get_condition(
                camera_id
            )

            condition.notify_all()

        return True

    def get_latest(self, camera_id):
        with self._lock:
            return self._frames.get(camera_id)

    def wait_for_frame(
        self,
        camera_id,
        last_sequence=0,
        timeout=1.0,
    ):
        condition = self._get_condition(
            camera_id
        )

        deadline = time.monotonic() + timeout

        with condition:
            current = self._frames.get(camera_id)

            if (
                current is not None
                and current.sequence != last_sequence
            ):
                return current

            remaining = max(
                0,
                deadline - time.monotonic(),
            )

            if remaining:
                condition.wait(
                    timeout=remaining
                )

            return self._frames.get(camera_id)

    def clear(self, camera_id):
        with self._lock:
            self._frames.pop(
                camera_id,
                None,
            )

    def clear_all(self):
        with self._lock:
            self._frames.clear()


camera_frame_hub = CameraFrameHub(
    jpeg_quality=72,
    max_width=1280,
)
