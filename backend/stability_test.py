from streaming.camera_monitor_manager import camera_monitor_manager as m
from streaming.camera_frame_hub import camera_frame_hub as h
from cameras.models import Camera
import time

camera_id = 13

print("START =", m.start_camera(camera_id))

started = time.time()
last_sequence = None
changes = 0
none_count = 0
max_age = 0.0

while time.time() - started < 600:
    packet = h.get_latest(camera_id)

    if packet is None:
        none_count += 1
        print(
            "NO FRAME",
            "ELAPSED=",
            round(time.time() - started, 1),
        )
    else:
        age = time.time() - packet.timestamp
        max_age = max(max_age, age)

        if last_sequence is None or packet.sequence != last_sequence:
            changes += 1

        last_sequence = packet.sequence

    time.sleep(1)

camera = Camera.objects.get(id=camera_id)

print()
print("========== RESULT ==========")
print("RUNNING =", m.is_running(camera_id))
print("STATUS =", camera.status)
print("LAST_SEEN =", camera.last_seen)
print("FRAME_CHANGES =", changes)
print("NO_FRAME_SAMPLES =", none_count)
print("MAX_FRAME_AGE =", round(max_age, 3))
print("=============================")
