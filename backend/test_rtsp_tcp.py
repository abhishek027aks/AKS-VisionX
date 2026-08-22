import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|rw_timeout;5000000"

import cv2
import time

url = r"rtsp://admin:<PASSWORD>@192.168.31.117:5543/live/channel0"

print("OpenCV:", cv2.__version__)

cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

print("OPEN:", cap.isOpened())

if cap.isOpened():
    print("WIDTH:", cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    print("HEIGHT:", cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("FPS:", cap.get(cv2.CAP_PROP_FPS))

    start = time.perf_counter()

    for i in range(10):
        t = time.perf_counter()
        ok, frame = cap.read()
        elapsed = (time.perf_counter() - t) * 1000

        print(
            "FRAME",
            i + 1,
            "OK=", ok,
            "READ_MS=", round(elapsed, 2),
            "SHAPE=", None if frame is None else frame.shape,
        )

    print(
        "TOTAL_SECONDS:",
        round(time.perf_counter() - start, 3)
    )

cap.release()
