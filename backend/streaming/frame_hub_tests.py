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

        packet = hub.get_latest(13)

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
        hub.publish(1, frame)

        packet = hub.get_latest(1)

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

        first = hub.get_latest(5)

        started = time.monotonic()

        second = hub.wait_for_frame(
            5,
            last_sequence=first.sequence - 1,
            timeout=0.2,
        )

        elapsed = time.monotonic() - started

        self.assertIsNotNone(second)
        self.assertEqual(
            second.sequence,
            first.sequence,
        )
        self.assertLess(
            elapsed,
            0.2,
        )

    def test_clear(self):
        hub = CameraFrameHub()

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        hub.publish(8, frame)
        hub.clear(8)

        self.assertIsNone(
            hub.get_latest(8)
        )
