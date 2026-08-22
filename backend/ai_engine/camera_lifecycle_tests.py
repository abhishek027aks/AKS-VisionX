from unittest.mock import patch

import numpy as np

from django.test import TestCase
from django.utils import timezone
from django.db import connection

from accounts.models import Organization
from cameras.models import Camera
from events.models import Detection, TrackingSession

from ai_engine.camera_inference_service import (
    CameraInferenceService,
)


class CameraInferenceLifecycleTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Phase 4 Camera Lifecycle Organization",
            slug="phase-4-camera-lifecycle-organization",
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="Phase 4 Lifecycle Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

    @patch(
        "ai_engine.camera_inference_service.end_stale_tracking_sessions"
    )
    @patch(
        "ai_engine.camera_inference_service.AIInferenceService"
    )
    @patch(
        "ai_engine.camera_inference_service.CameraStream"
    )
    def test_start_runs_tracking_cleanup_after_each_frame(
        self,
        stream_class,
        ai_service_class,
        cleanup,
    ):
        stream = stream_class.return_value
        ai_service = ai_service_class.return_value

        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8,
        )

        stream.read.return_value = frame

        ai_service.process_frame.return_value = {
            "detections": [],
            "sessions": [],
        }

        cleanup.return_value = 0

        service = CameraInferenceService(
            source=0,
            model_path="test-model.pt",
            tracking_timeout_seconds=45,
        )

        processed = service.start(
            camera=self.camera,
            zone="Zone A",
            max_frames=3,
        )

        self.assertEqual(
            processed,
            3,
        )

        self.assertEqual(
            stream.read.call_count,
            3,
        )

        self.assertEqual(
            ai_service.process_frame.call_count,
            3,
        )

        self.assertEqual(
            cleanup.call_count,
            3,
        )

        cleanup.assert_called_with(
            timeout_seconds=45,
        )

        stream.connect.assert_called_once()
        stream.release.assert_called_once()

        self.assertFalse(
            service.running
        )

    @patch(
        "ai_engine.camera_inference_service.end_stale_tracking_sessions"
    )
    @patch(
        "ai_engine.camera_inference_service.AIInferenceService"
    )
    @patch(
        "ai_engine.camera_inference_service.CameraStream"
    )
    def test_cleanup_returns_ended_session_count(
        self,
        stream_class,
        ai_service_class,
        cleanup,
    ):
        cleanup.return_value = 4

        service = CameraInferenceService(
            source=0,
            model_path="test-model.pt",
            tracking_timeout_seconds=20,
        )

        result = service.cleanup_stale_tracking()

        self.assertEqual(
            result,
            4,
        )

        cleanup.assert_called_once_with(
            timeout_seconds=20,
        )

    @patch(
        "ai_engine.camera_inference_service.end_stale_tracking_sessions"
    )
    @patch(
        "ai_engine.camera_inference_service.AIInferenceService"
    )
    @patch(
        "ai_engine.camera_inference_service.CameraStream"
    )
    def test_cleanup_is_run_even_when_no_detections_exist(
        self,
        stream_class,
        ai_service_class,
        cleanup,
    ):
        stream = stream_class.return_value
        ai_service = ai_service_class.return_value

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        stream.read.return_value = frame

        ai_service.process_frame.return_value = {
            "detections": [],
            "sessions": [],
        }

        cleanup.return_value = 2

        service = CameraInferenceService(
            source=0,
            model_path="test-model.pt",
            tracking_timeout_seconds=10,
        )

        processed = service.start(
            camera=self.camera,
            max_frames=2,
        )

        self.assertEqual(
            processed,
            2,
        )

        self.assertEqual(
            cleanup.call_count,
            2,
        )

        self.assertEqual(
            cleanup.return_value,
            2,
        )

        self.assertEqual(
            TrackingSession.objects.count(),
            0,
        )

        stream.release.assert_called_once()
    def test_real_webcam_yolo_lifecycle(
        self,
    ):
        import os

        model_path = r"E:\AKS VisionX\yolo11n.pt"

        if not os.path.exists(model_path):
            self.skipTest(
                f"YOLO model not found: {model_path}"
            )

        service = CameraInferenceService(
            source=0,
            model_path=model_path,
            tracker="bytetrack.yaml",
            confidence=0.25,
            reconnect_attempts=1,
            reconnect_delay=0,
            tracking_timeout_seconds=30,
        )

        processed = service.start(
            camera=self.camera,
            zone="Real Webcam Lifecycle Test",
            max_frames=1,
        )

        self.assertEqual(
            processed,
            1,
        )

        self.assertFalse(
            service.running,
        )

        self.assertFalse(
            service.stream.connected,
        )

        self.assertIsNone(
            service.stream.capture,
        )

        self.assertGreaterEqual(
            Detection.objects.count(),
            0,
        )

        self.assertGreaterEqual(
            TrackingSession.objects.count(),
            0,
        )
    def test_real_webcam_continuous_yolo_performance(
        self,
    ):
        import os
        import time

        model_path = r"E:\AKS VisionX\yolo11n.pt"

        if not os.path.exists(model_path):
            self.skipTest(
                f"YOLO model not found: {model_path}"
            )

        frame_count = 10

        service = CameraInferenceService(
            source=0,
            model_path=model_path,
            tracker="bytetrack.yaml",
            confidence=0.25,
            reconnect_attempts=1,
            reconnect_delay=0,
            tracking_timeout_seconds=30,
        )

        detections_before = Detection.objects.count()
        sessions_before = TrackingSession.objects.count()

        started_at = time.perf_counter()

        processed = service.start(
            camera=self.camera,
            zone="Real Webcam Continuous Performance Test",
            max_frames=frame_count,
        )

        elapsed = time.perf_counter() - started_at

        detections_after = Detection.objects.count()
        sessions_after = TrackingSession.objects.count()

        self.assertEqual(
            processed,
            frame_count,
        )

        self.assertFalse(
            service.running,
        )

        self.assertFalse(
            service.stream.connected,
        )

        self.assertIsNone(
            service.stream.capture,
        )

        detection_delta = (
            detections_after - detections_before
        )

        session_delta = (
            sessions_after - sessions_before
        )

        self.assertGreaterEqual(
            detection_delta,
            0,
        )

        self.assertGreaterEqual(
            session_delta,
            0,
        )

        self.assertGreater(
            elapsed,
            0,
        )

        average_fps = (
            processed / elapsed
        )

        print("")
        print("=== REAL WEBCAM CONTINUOUS PERFORMANCE ===")
        print("Frames requested:", frame_count)
        print("Frames processed:", processed)
        print("Elapsed seconds:", round(elapsed, 3))
        print("Average FPS:", round(average_fps, 2))
        print("New detections:", detection_delta)
        print("New tracking sessions:", session_delta)
        print("Stream connected after test:", service.stream.connected)
        print("Capture released:", service.stream.capture is None)
        print("=== PERFORMANCE TEST COMPLETE ===")
    def test_real_webcam_yolo_stage_profiling(
        self,
    ):
        import os
        import time

        model_path = r"E:\AKS VisionX\yolo11n.pt"

        if not os.path.exists(model_path):
            self.skipTest(
                f"YOLO model not found: {model_path}"
            )

        frame_count = 10

        service = CameraInferenceService(
            source=0,
            model_path=model_path,
            tracker="bytetrack.yaml",
            confidence=0.25,
            reconnect_attempts=1,
            reconnect_delay=0,
            tracking_timeout_seconds=30,
        )

        service.connect()

        read_times = []
        inference_times = []
        cleanup_times = []
        total_times = []

        total_detections = 0
        total_sessions = 0

        try:
            for frame_number in range(
                1,
                frame_count + 1,
            ):
                frame_started = time.perf_counter()

                read_started = time.perf_counter()

                frame = service.stream.read()

                read_elapsed = (
                    time.perf_counter()
                    - read_started
                )

                inference_started = time.perf_counter()

                result = service.ai_service.process_frame(
                    camera=self.camera,
                    frame=frame,
                    occurred_at=timezone.now(),
                    zone="Real Webcam Profiling Test",
                )

                inference_elapsed = (
                    time.perf_counter()
                    - inference_started
                )

                cleanup_started = time.perf_counter()

                service.cleanup_stale_tracking()

                cleanup_elapsed = (
                    time.perf_counter()
                    - cleanup_started
                )

                total_elapsed = (
                    time.perf_counter()
                    - frame_started
                )

                read_times.append(read_elapsed)
                inference_times.append(
                    inference_elapsed
                )
                cleanup_times.append(
                    cleanup_elapsed
                )
                total_times.append(total_elapsed)

                total_detections += len(
                    result["detections"]
                )

                total_sessions += len(
                    result["sessions"]
                )

        finally:
            service.running = False
            service.stream.release()

        total_elapsed = sum(total_times)

        average_read_ms = (
            sum(read_times)
            / len(read_times)
            * 1000
        )

        average_inference_ms = (
            sum(inference_times)
            / len(inference_times)
            * 1000
        )

        average_cleanup_ms = (
            sum(cleanup_times)
            / len(cleanup_times)
            * 1000
        )

        average_total_ms = (
            sum(total_times)
            / len(total_times)
            * 1000
        )

        average_fps = (
            frame_count / total_elapsed
        )

        self.assertEqual(
            len(read_times),
            frame_count,
        )

        self.assertEqual(
            len(inference_times),
            frame_count,
        )

        self.assertEqual(
            len(cleanup_times),
            frame_count,
        )

        self.assertFalse(
            service.stream.connected,
        )

        self.assertIsNone(
            service.stream.capture,
        )

        print("")
        print(
            "=== REAL WEBCAM YOLO STAGE PROFILING ==="
        )
        print(
            "Frames:",
            frame_count,
        )
        print(
            "Average camera read:",
            round(
                average_read_ms,
                2,
            ),
            "ms",
        )
        print(
            "Average YOLO + tracking + DB:",
            round(
                average_inference_ms,
                2,
            ),
            "ms",
        )
        print(
            "Average tracking cleanup:",
            round(
                average_cleanup_ms,
                2,
            ),
            "ms",
        )
        print(
            "Average total/frame:",
            round(
                average_total_ms,
                2,
            ),
            "ms",
        )
        print(
            "Estimated average FPS:",
            round(
                average_fps,
                2,
            ),
        )
        print(
            "Total detections returned:",
            total_detections,
        )
        print(
            "Total sessions returned:",
            total_sessions,
        )
        print(
            "Stream connected after test:",
            service.stream.connected,
        )
        print(
            "Capture released:",
            service.stream.capture is None,
        )
        print(
            "=== PROFILING COMPLETE ==="
        )

    def test_real_webcam_yolo_imgsz_profiling(
        self,
    ):
        import os
        import time

        model_path = r"E:\AKS VisionX\yolo11n.pt"

        if not os.path.exists(model_path):
            self.skipTest(
                f"YOLO model not found: {model_path}"
            )

        frame_count = 5
        image_sizes = [640, 416, 320]

        service = CameraInferenceService(
            source=0,
            model_path=model_path,
            tracker="bytetrack.yaml",
            confidence=0.25,
            reconnect_attempts=1,
            reconnect_delay=0,
            tracking_timeout_seconds=30,
        )

        service.connect()

        try:
            frame = service.stream.read()

            print("")
            print("=== YOLO IMGSZ PROFILING ===")

            for image_size in image_sizes:
                times = []
                detection_count = 0

                for _ in range(frame_count):
                    started = time.perf_counter()

                    results = service.ai_service.detector.model.track(
                        source=frame,
                        persist=True,
                        tracker=service.ai_service.detector.tracker,
                        conf=service.ai_service.detector.confidence,
                        imgsz=image_size,
                        verbose=False,
                    )

                    elapsed = (
                        time.perf_counter()
                        - started
                    )

                    times.append(elapsed)

                    if results:
                        result = results[0]

                        if result.boxes is not None:
                            detection_count += len(
                                result.boxes
                            )

                average_ms = (
                    sum(times)
                    / len(times)
                    * 1000
                )

                average_fps = (
                    1000 / average_ms
                    if average_ms > 0
                    else 0
                )

                print("")
                print(
                    f"Image size: {image_size}"
                )
                print(
                    "Average inference:",
                    round(average_ms, 2),
                    "ms",
                )
                print(
                    "Estimated inference FPS:",
                    round(average_fps, 2),
                )
                print(
                    "Total detections:",
                    detection_count,
                )

            print("")
            print("=== IMGSZ PROFILING COMPLETE ===")

        finally:
            service.running = False
            service.stream.release()

        self.assertFalse(
            service.stream.connected
        )

        self.assertIsNone(
            service.stream.capture
        )

    def test_real_webcam_yolo_vs_database_profiling(
        self,
    ):
        import os
        import time

        from events.models import Detection
        from events.tracking_service import update_tracking_session

        model_path = r"E:\AKS VisionX\yolo11n.pt"

        if not os.path.exists(model_path):
            self.skipTest(
                f"YOLO model not found: {model_path}"
            )

        frame_count = 10

        service = CameraInferenceService(
            source=0,
            model_path=model_path,
            tracker="bytetrack.yaml",
            confidence=0.25,
            reconnect_attempts=1,
            reconnect_delay=0,
            tracking_timeout_seconds=30,
        )

        service.connect()

        yolo_times = []
        database_times = []
        total_times = []

        total_detections = 0
        total_sessions = 0
        total_queries = 0

        try:
            for frame_number in range(
                1,
                frame_count + 1,
            ):
                frame_started = time.perf_counter()

                frame = service.stream.read()

                yolo_started = time.perf_counter()

                ai_detections = (
                    service.ai_service.detector.infer(
                        frame
                    )
                )

                yolo_elapsed = (
                    time.perf_counter()
                    - yolo_started
                )

                database_started = time.perf_counter()

                frame_detections = []
                frame_sessions = []

                query_count_before = len(
                    connection.queries
                )

                for ai_detection in ai_detections:
                    metadata = dict(
                        ai_detection.get(
                            "metadata",
                            {},
                        )
                    )

                    metadata["zone"] = (
                        "Real Webcam DB Profiling Test"
                    )

                    detection = Detection.objects.create(
                        organization=self.camera.organization,
                        camera=self.camera,
                        object_type=ai_detection[
                            "object_type"
                        ],
                        label=ai_detection.get(
                            "label",
                            "",
                        ),
                        confidence=ai_detection.get(
                            "confidence"
                        ),
                        tracking_id=ai_detection.get(
                            "tracking_id",
                            "",
                        ),
                        status=Detection.DetectionStatus.ACTIVE,
                        first_seen_at=timezone.now(),
                        last_seen_at=timezone.now(),
                        bbox_x=ai_detection.get(
                            "bbox_x"
                        ),
                        bbox_y=ai_detection.get(
                            "bbox_y"
                        ),
                        bbox_width=ai_detection.get(
                            "bbox_width"
                        ),
                        bbox_height=ai_detection.get(
                            "bbox_height"
                        ),
                        metadata=metadata,
                    )

                    frame_detections.append(
                        detection
                    )

                    session = update_tracking_session(
                        detection
                    )

                    if session is not None:
                        frame_sessions.append(
                            session
                        )

                query_count_after = len(
                    connection.queries
                )

                database_elapsed = (
                    time.perf_counter()
                    - database_started
                )

                total_elapsed = (
                    time.perf_counter()
                    - frame_started
                )

                yolo_times.append(
                    yolo_elapsed
                )

                database_times.append(
                    database_elapsed
                )

                total_times.append(
                    total_elapsed
                )

                total_detections += len(
                    frame_detections
                )

                total_sessions += len(
                    frame_sessions
                )

                total_queries += (
                    query_count_after
                    - query_count_before
                )

        finally:
            service.running = False
            service.stream.release()

        average_yolo_ms = (
            sum(yolo_times)
            / len(yolo_times)
            * 1000
        )

        average_database_ms = (
            sum(database_times)
            / len(database_times)
            * 1000
        )

        average_total_ms = (
            sum(total_times)
            / len(total_times)
            * 1000
        )

        average_queries = (
            total_queries / frame_count
        )

        average_fps = (
            frame_count
            / sum(total_times)
        )

        self.assertEqual(
            len(yolo_times),
            frame_count,
        )

        self.assertEqual(
            len(database_times),
            frame_count,
        )

        self.assertFalse(
            service.stream.connected,
        )

        self.assertIsNone(
            service.stream.capture,
        )

        print("")
        print(
            "=== YOLO VS DATABASE PROFILING ==="
        )
        print(
            "Frames:",
            frame_count,
        )
        print(
            "Average YOLO + ByteTrack:",
            round(
                average_yolo_ms,
                2,
            ),
            "ms",
        )
        print(
            "Average Detection + Tracking DB:",
            round(
                average_database_ms,
                2,
            ),
            "ms",
        )
        print(
            "Average total/frame:",
            round(
                average_total_ms,
                2,
            ),
            "ms",
        )
        print(
            "Average DB queries/frame:",
            round(
                average_queries,
                2,
            ),
        )
        print(
            "Estimated average FPS:",
            round(
                average_fps,
                2,
            ),
        )
        print(
            "Total detections:",
            total_detections,
        )
        print(
            "Total sessions:",
            total_sessions,
        )
        print(
            "Stream connected after test:",
            service.stream.connected,
        )
        print(
            "Capture released:",
            service.stream.capture is None,
        )
        print(
            "=== YOLO VS DATABASE PROFILING COMPLETE ==="
        )
