import time
from urllib.parse import urlsplit

import cv2


class CameraStreamError(Exception):
    """Raised when a camera stream cannot be opened or read."""
    pass


def normalize_camera_source(source):
    """Convert the stored local-camera URI into an OpenCV device index."""
    if not isinstance(source, str) or not source.lower().startswith("local://"):
        return source

    parsed = urlsplit(source)
    if parsed.scheme.lower() != "local" or parsed.path not in ("", "/"):
        raise ValueError("Local camera source must use local://<device-index>.")

    try:
        device_index = int(parsed.netloc)
    except (TypeError, ValueError):
        raise ValueError(
            "Local camera source must use a numeric device index."
        ) from None

    if device_index < 0 or device_index > 255:
        raise ValueError("Local camera device index must be between 0 and 255.")

    return device_index


class CameraStream:
    """
    OpenCV-based camera stream reader.

    Supports:
        - Windows local camera indexes
        - RTSP URLs
        - HTTP/HTTPS camera streams
        - reconnect attempts
        - read retries
        - FFmpeg network-stream timeouts
    """

    def __init__(
        self,
        source,
        reconnect_attempts=3,
        reconnect_delay=2,
        open_timeout_ms=10000,
        read_timeout_ms=10000,
    ):
        self.source = normalize_camera_source(source)
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.open_timeout_ms = open_timeout_ms
        self.read_timeout_ms = read_timeout_ms

        self.capture = None
        self.connected = False

    def _get_backend(self):
        """
        Select the OpenCV backend based on the source.

        Local camera indexes on Windows use DirectShow.
        Network streams use FFmpeg.
        """

        if isinstance(self.source, int):
            return cv2.CAP_DSHOW

        return cv2.CAP_FFMPEG

    def _open_capture(self):
        """Create and configure the underlying OpenCV capture."""

        backends = [self._get_backend()]
        if isinstance(self.source, int):
            backends.extend(
                backend
                for backend in (cv2.CAP_MSMF, cv2.CAP_ANY)
                if backend not in backends
            )

        capture = None
        for index, backend in enumerate(backends):
            try:
                capture = cv2.VideoCapture(self.source, backend)
            except cv2.error:
                capture = None
                continue

            if capture.isOpened():
                break

            if index < len(backends) - 1:
                capture.release()

        if capture is None:
            raise CameraStreamError(
                f"Unable to create camera stream: {self.source}"
            )

        try:
            capture.set(
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                self.open_timeout_ms,
            )
            capture.set(
                cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                self.read_timeout_ms,
            )
        except cv2.error:
            pass

        return capture

    def connect(self):
        """
        Open the configured camera/stream.

        Connection establishment only verifies that OpenCV
        successfully opened the source. Actual frame reading
        is handled by read().
        """

        self.release()

        for attempt in range(
            1,
            self.reconnect_attempts + 1,
        ):
            capture = self._open_capture()

            if capture.isOpened():
                self.capture = capture
                self.connected = True
                return True

            capture.release()
            self.capture = None
            self.connected = False

            if attempt < self.reconnect_attempts:
                time.sleep(self.reconnect_delay)

        raise CameraStreamError(
            f"Unable to open camera stream: {self.source}"
        )

    def _reconnect(self):
        """Release the current connection and reconnect."""

        self.release()

        return self.connect()

    def read(self):
        """
        Read one frame from the connected stream.

        A connection must already exist. If reading fails,
        the stream is marked disconnected and the configured
        reconnect attempts are used.
        """

        if self.capture is None or not self.connected:
            raise CameraStreamError(
                "Camera stream is not connected."
            )

        last_error = None

        for attempt in range(
            1,
            self.reconnect_attempts + 1,
        ):
            try:
                success, frame = self.capture.read()
            except cv2.error as exc:
                success, frame = False, None
                last_error = exc

            if success and frame is not None:
                return frame

            self.connected = False

            if attempt < self.reconnect_attempts:
                try:
                    self._reconnect()
                except CameraStreamError as exc:
                    last_error = exc

                if self.reconnect_delay > 0:
                    time.sleep(self.reconnect_delay)

                if self.capture is None or not self.connected:
                    continue

        if last_error is not None:
            raise CameraStreamError(
                "Failed to read frame from camera stream."
            ) from last_error

        raise CameraStreamError(
            "Failed to read frame from camera stream."
        )

    def get_properties(self):
        """Return basic stream properties."""

        if self.capture is None:
            return {}

        return {
            "width": int(
                self.capture.get(
                    cv2.CAP_PROP_FRAME_WIDTH
                )
            ),
            "height": int(
                self.capture.get(
                    cv2.CAP_PROP_FRAME_HEIGHT
                )
            ),
            "fps": self.capture.get(
                cv2.CAP_PROP_FPS
            ),
        }

    def release(self):
        """Release the underlying OpenCV capture."""

        if self.capture is not None:
            self.capture.release()

        self.capture = None
        self.connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.release()
