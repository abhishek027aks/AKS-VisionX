import time
import requests
from django.core import signing

camera_id = 13

token = signing.dumps(
    {
        "user_id": 1,
        "camera_id": camera_id,
    },
    salt="aks-visionx-live-stream",
)

url = (
    "http://127.0.0.1:8000"
    f"/api/cameras/{camera_id}/live/"
    f"?access_token={token}"
)

print("URL READY")
print("REQUESTING...")

started = time.time()

try:
    response = requests.get(
        url,
        stream=True,
        timeout=(5, 15),
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )

    print("STATUS =", response.status_code)
    print("CONTENT-TYPE =", response.headers.get("Content-Type"))
    print("CACHE-CONTROL =", response.headers.get("Cache-Control"))
    print()

    buffer = b""
    frames = 0
    bytes_received = 0
    first_frame_time = None
    last_frame_time = None

    for chunk in response.iter_content(
        chunk_size=65536
    ):
        if not chunk:
            continue

        now = time.time()
        bytes_received += len(chunk)
        buffer += chunk

        while b"--frame" in buffer:
            pos = buffer.find(b"--frame")
            frames += 1
            buffer = buffer[pos + len(b"--frame"):]

            if first_frame_time is None:
                first_frame_time = now

            last_frame_time = now

        if now - started >= 10:
            break

    print("ELAPSED =", round(time.time() - started, 2))
    print("FRAMES =", frames)
    print("BYTES =", bytes_received)
    print(
        "FIRST_FRAME_DELAY =",
        None
        if first_frame_time is None
        else round(
            first_frame_time - started,
            3,
        ),
    )
    print(
        "LAST_FRAME_AGE =",
        None
        if last_frame_time is None
        else round(
            time.time() - last_frame_time,
            3,
        ),
    )

except Exception as exc:
    print("ERROR =", type(exc).__name__)
    print("DETAIL =", exc)
