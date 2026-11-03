from streaming.camera_stream_service import CameraStream

stream = CameraStream(
    source=0,
    reconnect_attempts=3,
    reconnect_delay=1,
)

print("Connecting to webcam index 0...")

stream.connect()

print("CONNECTED:", stream.connected)
print("PROPERTIES:", stream.get_properties())

frame = stream.read()

print("FRAME:", frame.shape)

stream.release()

print("RESULT: CAMERA STREAM TEST PASSED")
