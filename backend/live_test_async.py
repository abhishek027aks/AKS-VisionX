from streaming.camera_monitor_manager import camera_monitor_manager as m
from streaming.camera_frame_hub import camera_frame_hub as h
import time

camera_id = 13

print("START =", m.start_camera(camera_id))

time.sleep(5)

last = None
changes = 0
samples = []

for i in range(30):
    p = h.get_latest(camera_id)

    if p is None:
        samples.append(
            (i, None, None, None)
        )
    else:
        changed = (
            last is None
            or p.sequence != last
        )

        if changed:
            changes += 1

        samples.append(
            (
                i,
                p.sequence,
                changed,
                round(
                    time.time() - p.timestamp,
                    3,
                ),
            )
        )

        last = p.sequence

    time.sleep(0.5)

print("SAMPLES=")

for row in samples:
    print(row)

print("CHANGES=", changes)
print("RUNNING=", m.is_running(camera_id))

print("STOP=", m.stop_camera(camera_id))
