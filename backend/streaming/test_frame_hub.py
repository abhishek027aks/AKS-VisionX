import threading
import time

import cv2
import numpy as np
from django.test import SimpleTestCase

from streaming.camera_frame_hub import (
    CameraFrameHub,
)


class CameraFrameHubTests(SimpleTestCase):

    def test_publish_and_get_latest(self):
        hub = CameraFrameHub(
            jpeg_quality=70,
            max_width=640,
        )

        frame = np.zeros(
            (480, 1280, 3),
            dtype=np.uint8,
        )

        self.assertTrue(
            hub.publish(
                13,
                frame,
            )
        )

        packet = hub.wait_for_frame(13, timeout=1.0)

        self.assertIsNotNone(packet)

        self.assertEqual(
            packet.sequence,
            1,
        )

        self.assertEqual(
            packet.width,
            640,
        )

        self.assertGreater(
            len(packet.jpeg),
            0,
        )

        decoded = cv2.imdecode(
            np.frombuffer(
                packet.jpeg,
                dtype=np.uint8,
            ),
            cv2.IMREAD_COLOR,
        )

        self.assertIsNotNone(decoded)

    def test_sequence_increments(self):
        hub = CameraFrameHub()

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        hub.publish(1, frame)
        first = hub.wait_for_frame(1, timeout=1.0)
        self.assertIsNotNone(first)

        hub.publish(1, frame)
        packet = hub.wait_for_frame(
            1,
            last_sequence=first.sequence,
            timeout=1.0,
        )

        self.assertEqual(
            packet.sequence,
            2,
        )

    def test_wait_returns_newer_frame(self):
        hub = CameraFrameHub()

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        hub.publish(5, frame)

        first = hub.wait_for_frame(5, timeout=1.0)
        self.assertIsNotNone(first)

        started = time.monotonic()

        hub.publish(5, frame)
        second = hub.wait_for_frame(
            5,
            last_sequence=first.sequence,
            timeout=1.0,
        )

        elapsed = time.monotonic() - started

        self.assertIsNotNone(second)
        self.assertGreater(second.sequence, first.sequence)
        self.assertLess(
            elapsed,
            1.0,
        )

    def test_clear(self):
        hub = CameraFrameHub()

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        hub.publish(8, frame)
        self.assertIsNotNone(hub.wait_for_frame(8, timeout=1.0))
        hub.clear(8)

        self.assertIsNone(
            hub.get_latest(8)
        )

    def test_clear_does_not_restore_frame_being_encoded(self):
        hub = CameraFrameHub()
        encoding_started = threading.Event()
        finish_encoding = threading.Event()

        def delayed_encode(frame):
            encoding_started.set()
            finish_encoding.wait()
            return b"jpeg", 100, 100

        hub._encode = delayed_encode
        hub.publish(9, np.zeros((100, 100, 3), dtype=np.uint8))
        worker = hub._threads[9]

        try:
            self.assertTrue(encoding_started.wait(timeout=1.0))
            hub.clear(9)
        finally:
            finish_encoding.set()
            worker.join(timeout=1.0)

        self.assertFalse(worker.is_alive())
        self.assertIsNone(hub.get_latest(9))
