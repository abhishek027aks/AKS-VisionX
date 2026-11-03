import cv2
from ai_engine.detection_service import YOLODetectionService

IMAGE = r".\yolo_test.jpg"

frame = cv2.imread(IMAGE)

if frame is None:
    raise SystemExit(f"ERROR: Unable to read {IMAGE}")

service = YOLODetectionService(
    model_path="yolo11n.pt",
    confidence=0.25,
)

detections = service.infer(frame, persist=False)

print()
print("========================================")
print("YOLO REAL FRAME TEST")
print("========================================")
print("Frame shape:", frame.shape)
print("Detections:", len(detections))
print()

for index, detection in enumerate(detections, start=1):
    print(f"Detection #{index}")
    print("  object_type :", detection["object_type"])
    print("  label       :", detection["label"])
    print("  confidence  :", detection["confidence"])
    print("  tracking_id :", detection["tracking_id"])
    print("  bbox        :",
          detection["bbox_x"],
          detection["bbox_y"],
          detection["bbox_width"],
          detection["bbox_height"])
    print("  metadata    :", detection["metadata"])
    print()

print("RESULT: YOLO INFERENCE TEST PASSED")
