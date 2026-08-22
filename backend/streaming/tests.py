from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from streaming.camera_stream_service import (
    CameraStream,
    CameraStreamError,
)


class CameraStreamTests(SimpleTestCase):

    @patch(
        "streaming.camera_stream_service.cv2.VideoCapture"
    )
    def test_connect_success(self, video_capture):
        capture = MagicMock()
        capture.isOpened.return_value = True
        video_capture.return_value = capture

        stream = CameraStream(
            source=0,
            reconnect_attempts=3,
            reconnect_delay=0,
        )

        result = stream.connect()

        self.assertTrue(result)
        self.assertTrue(stream.connected)
        self.assertIs(stream.capture, capture)

        video_capture.assert_called_once_with(
            0,
            stream_module_cv2_dshow(),
        )

    @patch(
        "streaming.camera_stream_service.cv2.VideoCapture"
    )
    def test_rtsp_source_uses_ffmpeg(
        self,
        video_capture,
    ):
        capture = MagicMock()
        capture.isOpened.return_value = True
        video_capture.return_value = capture

        source = "rtsp://test-camera/stream"

        stream = CameraStream(
            source=source,
            reconnect_attempts=1,
            reconnect_delay=0,
        )

        result = stream.connect()

        self.assertTrue(result)

        video_capture.assert_called_once_with(
            source,
            stream_module_cv2_ffmpeg(),
        )

    @patch(
        "streaming.camera_stream_service.cv2.VideoCapture"
    )
    def test_connect_retries_then_succeeds(
        self,
        video_capture,
    ):
        failed_capture = MagicMock()
        failed_capture.isOpened.return_value = False

        successful_capture = MagicMock()
        successful_capture.isOpened.return_value = True

        video_capture.side_effect = [
            failed_capture,
            successful_capture,
        ]

        stream = CameraStream(
            source="rtsp://test-camera",
            reconnect_attempts=2,
            reconnect_delay=0,
        )

        result = stream.connect()

        self.assertTrue(result)
        self.assertTrue(stream.connected)
        self.assertIs(
            stream.capture,
            successful_capture,
        )

        self.assertEqual(
            video_capture.call_count,
            2,
        )

        failed_capture.release.assert_called_once()

    @patch(
        "streaming.camera_stream_service.cv2.VideoCapture"
    )
    def test_connect_failure_after_all_attempts(
        self,
        video_capture,
    ):
        capture = MagicMock()
        capture.isOpened.return_value = False

        video_capture.return_value = capture

        stream = CameraStream(
            source="rtsp://invalid-camera",
            reconnect_attempts=3,
            reconnect_delay=0,
        )

        with self.assertRaises(
            CameraStreamError
        ):
            stream.connect()

        self.assertFalse(stream.connected)
        self.assertIsNone(stream.capture)

        self.assertEqual(
            video_capture.call_count,
            3,
        )

        self.assertEqual(
            capture.release.call_count,
            3,
        )

    def test_read_requires_connection(self):
        stream = CameraStream(
            source=0,
        )

        with self.assertRaises(
            CameraStreamError
        ):
            stream.read()

    @patch(
        "streaming.camera_stream_service.cv2.VideoCapture"
    )
    def test_read_returns_frame(
        self,
        video_capture,
    ):
        capture = MagicMock()
        capture.isOpened.return_value = True

        frame = object()

        capture.read.return_value = (
            True,
            frame,
        )

        video_capture.return_value = capture

        stream = CameraStream(
            source=0,
            reconnect_attempts=1,
            reconnect_delay=0,
        )

        stream.connect()

        result = stream.read()

        self.assertIs(result, frame)

        capture.read.assert_called_once()

        self.assertTrue(stream.connected)

    @patch(
        "streaming.camera_stream_service.cv2.VideoCapture"
    )
    def test_read_failure_marks_stream_disconnected(
        self,
        video_capture,
    ):
        capture = MagicMock()
        capture.isOpened.return_value = True

        capture.read.return_value = (
            False,
            None,
        )

        video_capture.return_value = capture

        stream = CameraStream(
            source=0,
            reconnect_attempts=1,
            reconnect_delay=0,
        )

        stream.connect()

        with self.assertRaises(
            CameraStreamError
        ):
            stream.read()

        self.assertFalse(stream.connected)

    @patch(
        "streaming.camera_stream_service.cv2.VideoCapture"
    )
    def test_get_properties(
        self,
        video_capture,
    ):
        capture = MagicMock()
        capture.isOpened.return_value = True

        capture.get.side_effect = lambda property_id: {
            3: 1920,
            4: 1080,
            5: 25.0,
        }.get(property_id, 0)

        video_capture.return_value = capture

        stream = CameraStream(
            source=0,
            reconnect_attempts=1,
            reconnect_delay=0,
        )

        stream.connect()

        properties = stream.get_properties()

        self.assertEqual(
            properties["width"],
            1920,
        )

        self.assertEqual(
            properties["height"],
            1080,
        )

        self.assertEqual(
            properties["fps"],
            25.0,
        )

    def test_get_properties_without_capture(self):
        stream = CameraStream(
            source=0,
        )

        self.assertEqual(
            stream.get_properties(),
            {},
        )

    @patch(
        "streaming.camera_stream_service.cv2.VideoCapture"
    )
    def test_release(
        self,
        video_capture,
    ):
        capture = MagicMock()
        capture.isOpened.return_value = True

        video_capture.return_value = capture

        stream = CameraStream(
            source=0,
            reconnect_attempts=1,
            reconnect_delay=0,
        )

        stream.connect()
        stream.release()

        capture.release.assert_called_once()

        self.assertIsNone(stream.capture)
        self.assertFalse(stream.connected)

    @patch(
        "streaming.camera_stream_service.cv2.VideoCapture"
    )
    def test_context_manager(
        self,
        video_capture,
    ):
        capture = MagicMock()
        capture.isOpened.return_value = True

        video_capture.return_value = capture

        with CameraStream(
            source=0,
            reconnect_attempts=1,
            reconnect_delay=0,
        ) as stream:
            self.assertTrue(stream.connected)

        capture.release.assert_called_once()


def stream_module_cv2_dshow():
    import cv2
    return cv2.CAP_DSHOW


def stream_module_cv2_ffmpeg():
    import cv2
    return cv2.CAP_FFMPEG
