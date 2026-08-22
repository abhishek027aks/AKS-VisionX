from cameras.models import Camera
from streaming.camera_monitor_manager import CameraMonitorManager
from streaming.camera_stream_service import CameraStream
import time

camera = Camera.objects.get(id=13)

stream = camera.streams.filter(
    stream_type="MAIN",
    enabled=True
).first()

url = CameraMonitorManager._build_authenticated_stream_url(
    camera,
    stream.url,
)

print("URL HOST TEST OK")

capture = CameraStream(
    source=url,
    reconnect_attempts=1,
    reconnect_delay=0,
    open_timeout_ms=5000,
    read_timeout_ms=3000,
)

print("CONNECTING...")

capture.connect()

print("CONNECTED")

start = time.perf_counter()
frames = 0
last_shape = None

while time.perf_counter() - start < 5:
    frame = capture.read()

    if frame is not None:
        frames += 1
        last_shape = frame.shape

elapsed = time.perf_counter() - start

print("FRAMES =", frames)
print("FPS =", round(frames / elapsed, 2))
print("FRAME =", last_shape)
print("TIME =", round(elapsed, 2), "seconds")

capture.release()

print("RELEASED")
