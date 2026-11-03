import queue
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
    Latest-frame live hub.

    RTSP capture never performs JPEG encoding.
    Only the newest raw frame is retained for encoding.

    This is intentionally a latest-frame architecture:
    old frames are discarded instead of building latency.
    """

    def __init__(
        self,
        jpeg_quality=55,
        max_width=960,
    ):
        self.jpeg_quality = int(jpeg_quality)
        self.max_width = int(max_width)

        self._frames = {}
        self._queues = {}
        self._threads = {}
        self._stop_events = {}
        self._conditions = {}
        self._lock = threading.RLock()

    def _get_condition(self, camera_id):
        with self._lock:
            condition = self._conditions.get(camera_id)

            if condition is None:
                condition = threading.Condition(self._lock)
                self._conditions[camera_id] = condition

            return condition

    def start(self, camera_id):
        with self._lock:
            existing = self._threads.get(camera_id)

            if (
                existing is not None
                and existing.is_alive()
            ):
                return False

            frame_queue = queue.Queue(maxsize=1)
            stop_event = threading.Event()

            thread = threading.Thread(
                target=self._encoder_worker,
                args=(
                    camera_id,
                    frame_queue,
                    stop_event,
                ),
                daemon=True,
                name=f"camera-live-encoder-{camera_id}",
            )

            self._queues[camera_id] = frame_queue
            self._stop_events[camera_id] = stop_event
            self._threads[camera_id] = thread

            thread.start()

            return True

    @staticmethod
    def _offer_latest(frame_queue, frame):
        try:
            frame_queue.put_nowait(frame)
            return
        except queue.Full:
            pass

        try:
            frame_queue.get_nowait()
        except queue.Empty:
            pass

        try:
            frame_queue.put_nowait(frame)
        except queue.Full:
            pass

    def publish(self, camera_id, frame):
        if frame is None:
            return False

        self.start(camera_id)

        with self._lock:
            frame_queue = self._queues.get(camera_id)

        if frame_queue is None:
            return False

        self._offer_latest(
            frame_queue,
            frame,
        )

        return True

    def _encode(self, frame):
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
            return None

        return (
            encoded.tobytes(),
            image.shape[1],
            image.shape[0],
        )

    def _encoder_worker(
        self,
        camera_id,
        frame_queue,
        stop_event,
    ):
        while not stop_event.is_set():
            try:
                frame = frame_queue.get(
                    timeout=0.25
                )
            except queue.Empty:
                continue

            if frame is None:
                continue

            try:
                result = self._encode(frame)

                if result is None:
                    continue

                jpeg, width, height = result

                with self._lock:
                    if stop_event.is_set():
                        continue

                    previous = self._frames.get(
                        camera_id
                    )

                    sequence = (
                        previous.sequence + 1
                        if previous is not None
                        else 1
                    )

                    self._frames[camera_id] = FramePacket(
                        sequence=sequence,
                        jpeg=jpeg,
                        timestamp=time.time(),
                        width=width,
                        height=height,
                    )

                    condition = self._get_condition(
                        camera_id
                    )

                    condition.notify_all()

            except Exception:
                # Encoder errors must never stop RTSP capture.
                continue

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
            current = self._frames.get(
                camera_id
            )

            if (
                current is not None
                and current.sequence > last_sequence
            ):
                return current

            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return self._frames.get(camera_id)

                condition.wait(
                    timeout=remaining
                )

                current = self._frames.get(camera_id)
                if (
                    current is not None
                    and current.sequence > last_sequence
                ):
                    return current

    def clear(self, camera_id):
        with self._lock:
            stop_event = self._stop_events.pop(
                camera_id,
                None,
            )
            if stop_event is not None:
                stop_event.set()

            self._frames.pop(
                camera_id,
                None,
            )

            thread = self._threads.pop(
                camera_id,
                None,
            )

            self._queues.pop(
                camera_id,
                None,
            )

        if stop_event is not None:
            stop_event.set()

        if (
            thread is not None
            and thread is not threading.current_thread()
            and thread.is_alive()
        ):
            thread.join(timeout=1.0)

    def clear_all(self):
        with self._lock:
            camera_ids = set(self._frames)
            camera_ids.update(self._queues)
            camera_ids.update(self._threads)

        for camera_id in camera_ids:
            self.clear(camera_id)


camera_frame_hub = CameraFrameHub(
    jpeg_quality=55,
    max_width=960,
)