import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

import django

django.setup()

from cameras.models import Camera
from ai_engine.camera_inference_service import CameraInferenceService


camera = Camera.objects.get(id=13)

print("========================================")
print("REAL WEBCAM AI PIPELINE TEST")
print("========================================")
print("Camera ID:", camera.id)
print("Camera:", camera.name)
print("Connection type:", camera.connection_type)
print("Enabled:", camera.enabled)


service = CameraInferenceService(
    source=0,
    model_path="yolo11n.pt",
    tracker="bytetrack.yaml",
    confidence=0.25,
    reconnect_attempts=3,
    reconnect_delay=1,
    tracking_timeout_seconds=30,
)


result = service.start(
    camera=camera,
    zone="WEBCAM_TEST",
    max_frames=10,
)


print()
print("========================================")
print("PIPELINE RESULT")
print("========================================")
print("Processed frames:", result)
print("========================================")
