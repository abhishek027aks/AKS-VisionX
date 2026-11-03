from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np

from django.test import SimpleTestCase

from ai_engine.detection_service import (
    AIDetectionError,
    YOLODetectionService,
)


class FakeValue:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value

    def tolist(self):
        return self.value


class FakeBox:
    def __init__(
        self,
        class_id,
        confidence,
        bbox,
    ):
        self.cls = FakeValue(class_id)
        self.conf = FakeValue(confidence)
        self.xyxy = [FakeValue(bbox)]


class FakeBoxes:
    def __init__(
        self,
        boxes,
        tracking_ids=None,
    ):
        self._boxes = boxes

        if tracking_ids is None:
            self.id = None
        else:
            self.id = FakeValue(tracking_ids)

    def __iter__(self):
        return iter(self._boxes)

    def __len__(self):
        return len(self._boxes)


class FakeResult:
    def __init__(
        self,
        boxes,
        names,
    ):
        self.boxes = boxes
        self.names = names


class YOLODetectionServiceTests(SimpleTestCase):

    @patch("ai_engine.detection_service.YOLO")
    def test_initializes_yolo_model(
        self,
        yolo_class,
    ):
        model = yolo_class.return_value

        service = YOLODetectionService(
            model_path="test-model.pt",
            tracker="bytetrack.yaml",
            confidence=0.30,
        )

        yolo_class.assert_called_once_with(
            "test-model.pt"
        )

        self.assertIs(
            service.model,
            model,
        )

        self.assertEqual(
            service.model_path,
            "test-model.pt",
        )

        self.assertEqual(
            service.tracker,
            "bytetrack.yaml",
        )

        self.assertEqual(
            service.confidence,
            0.30,
        )

    @patch("ai_engine.detection_service.YOLO")
    def test_infer_converts_yolo_result(
        self,
        yolo_class,
    ):
        model = yolo_class.return_value

        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8,
        )

        box = FakeBox(
            class_id=0,
            confidence=0.91,
            bbox=[64, 48, 320, 240],
        )

        boxes = FakeBoxes(
            boxes=[box],
            tracking_ids=[7],
        )

        result = FakeResult(
            boxes=boxes,
            names={
                0: "person",
            },
        )

        model.track.return_value = [
            result
        ]

        service = YOLODetectionService(
            model_path="test-model.pt",
            tracker="bytetrack.yaml",
            confidence=0.25,
        )

        detections = service.infer(
            frame,
            persist=True,
        )

        model.track.assert_called_once_with(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=0.25,
            imgsz=416,
            verbose=False,
        )

        self.assertEqual(
            len(detections),
            1,
        )

        detection = detections[0]

        self.assertEqual(
            detection["object_type"],
            "PERSON",
        )

        self.assertEqual(
            detection["label"],
            "person",
        )

        self.assertEqual(
            detection["confidence"],
            Decimal("0.91"),
        )

        self.assertEqual(
            detection["tracking_id"],
            "7",
        )

        self.assertEqual(
            detection["bbox_x"],
            Decimal("0.100000"),
        )

        self.assertEqual(
            detection["bbox_y"],
            Decimal("0.100000"),
        )

        self.assertEqual(
            detection["bbox_width"],
            Decimal("0.400000"),
        )

        self.assertEqual(
            detection["bbox_height"],
            Decimal("0.400000"),
        )

        self.assertEqual(
            detection["metadata"]["model"],
            "test-model.pt",
        )

        self.assertEqual(
            detection["metadata"]["class_id"],
            0,
        )

    @patch("ai_engine.detection_service.YOLO")
    def test_infer_maps_vehicle_classes(
        self,
        yolo_class,
    ):
        model = yolo_class.return_value

        frame = np.zeros(
            (100, 200, 3),
            dtype=np.uint8,
        )

        boxes = FakeBoxes(
            boxes=[
                FakeBox(
                    class_id=0,
                    confidence=0.80,
                    bbox=[0, 0, 100, 50],
                ),
                FakeBox(
                    class_id=1,
                    confidence=0.75,
                    bbox=[20, 10, 120, 60],
                ),
                FakeBox(
                    class_id=2,
                    confidence=0.70,
                    bbox=[40, 20, 140, 70],
                ),
            ],
            tracking_ids=[
                1,
                2,
                3,
            ],
        )

        result = FakeResult(
            boxes=boxes,
            names={
                0: "car",
                1: "bus",
                2: "truck",
            },
        )

        model.track.return_value = [
            result
        ]

        service = YOLODetectionService(
            model_path="test-model.pt",
        )

        detections = service.infer(
            frame,
        )

        self.assertEqual(
            len(detections),
            3,
        )

        self.assertEqual(
            detections[0]["object_type"],
            "VEHICLE",
        )

        self.assertEqual(
            detections[1]["object_type"],
            "VEHICLE",
        )

        self.assertEqual(
            detections[2]["object_type"],
            "VEHICLE",
        )

    @patch("ai_engine.detection_service.YOLO")
    def test_infer_maps_supported_animals_and_preserves_species(
        self,
        yolo_class,
    ):
        model = yolo_class.return_value
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        model.track.return_value = [
            FakeResult(
                boxes=FakeBoxes(
                    boxes=[
                        FakeBox(0, 0.91, [0, 0, 40, 40]),
                        FakeBox(1, 0.88, [50, 0, 90, 40]),
                        FakeBox(2, 0.83, [100, 0, 140, 40]),
                        FakeBox(3, 0.79, [150, 0, 190, 40]),
                    ],
                    tracking_ids=[1, 2, 3, 4],
                ),
                names={
                    0: "dog",
                    1: "Cat",
                    2: "water buffalo",
                    3: "goat",
                },
            )
        ]

        service = YOLODetectionService(model_path="animal-model.pt")
        detections = service.infer(frame)

        self.assertEqual(
            [item["object_type"] for item in detections],
            ["ANIMAL"] * 4,
        )
        self.assertEqual(
            [item["metadata"]["species"] for item in detections],
            ["dog", "cat", "water buffalo", "goat"],
        )
        self.assertEqual(
            [item["tracking_id"] for item in detections],
            ["1", "2", "3", "4"],
        )

    @patch("ai_engine.detection_service.YOLO")
    def test_infer_without_tracking_ids(
        self,
        yolo_class,
    ):
        model = yolo_class.return_value

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        boxes = FakeBoxes(
            boxes=[
                FakeBox(
                    class_id=0,
                    confidence=0.88,
                    bbox=[10, 10, 50, 50],
                )
            ],
            tracking_ids=None,
        )

        result = FakeResult(
            boxes=boxes,
            names={
                0: "person",
            },
        )

        model.track.return_value = [
            result
        ]

        service = YOLODetectionService(
            model_path="test-model.pt",
        )

        detections = service.infer(
            frame,
        )

        self.assertEqual(
            detections[0]["tracking_id"],
            "",
        )

    @patch("ai_engine.detection_service.YOLO")
    def test_infer_returns_empty_when_no_results(
        self,
        yolo_class,
    ):
        model = yolo_class.return_value

        model.track.return_value = []

        service = YOLODetectionService(
            model_path="test-model.pt",
        )

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        detections = service.infer(frame)

        self.assertEqual(
            detections,
            [],
        )

    @patch("ai_engine.detection_service.YOLO")
    def test_infer_returns_empty_when_boxes_are_none(
        self,
        yolo_class,
    ):
        model = yolo_class.return_value

        result = FakeResult(
            boxes=None,
            names={},
        )

        model.track.return_value = [
            result
        ]

        service = YOLODetectionService(
            model_path="test-model.pt",
        )

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        detections = service.infer(frame)

        self.assertEqual(
            detections,
            [],
        )

    @patch("ai_engine.detection_service.YOLO")
    def test_infer_wraps_yolo_error(
        self,
        yolo_class,
    ):
        model = yolo_class.return_value

        model.track.side_effect = RuntimeError(
            "YOLO failed"
        )

        service = YOLODetectionService(
            model_path="test-model.pt",
        )

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        with self.assertRaises(
            AIDetectionError
        ):
            service.infer(frame)

    @patch("ai_engine.detection_service.YOLO")
    def test_model_load_error_is_wrapped(
        self,
        yolo_class,
    ):
        yolo_class.side_effect = RuntimeError(
            "model unavailable"
        )

        with self.assertRaises(
            AIDetectionError
        ):
            YOLODetectionService(
                model_path="missing-model.pt",
            )
