from decimal import Decimal

from ultralytics import YOLO


class AIDetectionError(Exception):
    """Raised when AI inference fails."""
    pass


class YOLODetectionService:
    """
    YOLO-based object detection and tracking service.

    The service converts YOLO output into a backend-friendly
    detection structure containing:
        - object type
        - label
        - confidence
        - tracking ID
        - normalized bounding box
    """

    OBJECT_TYPE_MAP = {
        "person": "PERSON",
        "car": "VEHICLE",
        "motorcycle": "VEHICLE",
        "bus": "VEHICLE",
        "truck": "VEHICLE",
        "bicycle": "VEHICLE",
    }

    def __init__(
        self,
        model_path="yolo11n.pt",
        tracker="bytetrack.yaml",
        confidence=0.25,
        imgsz=416,
    ):
        self.model_path = model_path
        self.tracker = tracker
        self.confidence = confidence
        self.imgsz = imgsz

        try:
            self.model = YOLO(model_path)
        except Exception as exc:
            raise AIDetectionError(
                f"Unable to load YOLO model: {model_path}"
            ) from exc

    def infer(self, frame, persist=True):
        """
        Run YOLO tracking on one frame.

        Returns a list of normalized detection dictionaries.
        """

        try:
            results = self.model.track(
                source=frame,
                persist=persist,
                tracker=self.tracker,
                conf=self.confidence,
                imgsz=self.imgsz,
                verbose=False,
            )
        except Exception as exc:
            raise AIDetectionError(
                "YOLO inference failed."
            ) from exc

        if not results:
            return []

        result = results[0]

        if result.boxes is None:
            return []

        boxes = result.boxes

        names = result.names

        frame_height, frame_width = frame.shape[:2]

        tracking_ids = (
            boxes.id.tolist()
            if boxes.id is not None
            else [None] * len(boxes)
        )

        detections = []

        for index, box in enumerate(boxes):
            class_id = int(box.cls.item())

            label = names[class_id]

            confidence = float(box.conf.item())

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            width = x2 - x1
            height = y2 - y1

            normalized_x = x1 / frame_width
            normalized_y = y1 / frame_height
            normalized_width = width / frame_width
            normalized_height = height / frame_height

            object_type = self.OBJECT_TYPE_MAP.get(
                label,
                "OBJECT",
            )

            tracking_id = tracking_ids[index]

            if tracking_id is not None:
                tracking_id = str(int(tracking_id))

            detections.append(
                {
                    "object_type": object_type,
                    "label": label,
                    "confidence": Decimal(
                        f"{confidence:.2f}"
                    ),
                    "tracking_id": tracking_id or "",
                    "bbox_x": Decimal(
                        f"{normalized_x:.6f}"
                    ),
                    "bbox_y": Decimal(
                        f"{normalized_y:.6f}"
                    ),
                    "bbox_width": Decimal(
                        f"{normalized_width:.6f}"
                    ),
                    "bbox_height": Decimal(
                        f"{normalized_height:.6f}"
                    ),
                    "metadata": {
                        "model": self.model_path,
                        "class_id": class_id,
                    },
                }
            )

        return detections
