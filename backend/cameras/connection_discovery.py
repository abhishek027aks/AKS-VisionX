import socket
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlparse, urlunparse


@dataclass
class CameraConnectionRequest:
    camera_type: str
    host: str = ""
    username: str = ""
    password: str = ""
    stream_url: str = ""
    port: int | None = None
    stream_path: str = ""
    device_index: int | str | None = None


class CameraConnectionDiscoveryService:
    """Probe a new camera without creating a Camera database record."""

    RTSP_PORT = 554
    ONVIF_PORTS = (80, 8080, 8899, 8000, 2020, 5000)
    RTSP_PATHS = (
        "stream1", "stream2", "stream", "live", "live/ch0", "h264",
        "cam/realmonitor?channel=1&subtype=0",
        "cam/realmonitor?channel=1&subtype=1",
        "Streaming/Channels/101", "Streaming/Channels/102",
        "axis-media/media.amp", "videoMain", "videoSub",
        "live/ch00_0", "live/ch00_1", "unicast/c1/s0/live",
        "media/video1", "onvif1", "h264Preview_01_main",
        "h264Preview_01_sub",
    )
    LOCAL_CAMERA_SCAN_LIMIT = 10
    ONVIF_DISCOVERY_ADDRESS = ("239.255.255.250", 3702)
    ONVIF_DISCOVERY_TIMEOUT_SECONDS = 2.0
    ONVIF_DISCOVERY_PROBE = b"""<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
 xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
 xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
 xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <e:Header>
    <w:MessageID>urn:uuid:visionx-camera-discovery</w:MessageID>
    <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body>
</e:Envelope>"""

    @classmethod
    def discover_local_cameras(cls):
        """Find cameras attached to the backend host; do not retain captures."""
        devices = []
        failures = []
        for device_index in range(cls.LOCAL_CAMERA_SCAN_LIMIT):
            result = cls()._validate_local_camera(device_index)
            if result["success"]:
                devices.append(
                    {
                        "device_index": device_index,
                        "name": f"Camera {device_index}",
                        "stream_url": result["stream_url"],
                        "width": result["width"],
                        "height": result["height"],
                        "fps": max(0, result["fps"]),
                    }
                )
            elif result.get("error_code") not in {
                "DEVICE_NOT_FOUND",
                "TIMEOUT",
            }:
                failures.append(result["message"])

        return {
            "devices": devices,
            "message": (
                f"Found {len(devices)} local camera(s)."
                if devices
                else (
                    "No local cameras were detected. Connect the webcam "
                    "to the PC running the backend and try again."
                )
            ),
            "warning": failures[0] if failures else "",
        }

    @classmethod
    def discover_onvif_devices(cls):
        """Send a bounded ONVIF WS-Discovery probe on the local network."""
        import xml.etree.ElementTree as element_tree

        devices = {}
        probe_socket = None
        try:
            probe_socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP,
            )
            probe_socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_MULTICAST_TTL,
                2,
            )
            probe_socket.settimeout(cls.ONVIF_DISCOVERY_TIMEOUT_SECONDS)
            probe_socket.sendto(
                cls.ONVIF_DISCOVERY_PROBE,
                cls.ONVIF_DISCOVERY_ADDRESS,
            )
            import time

            end_time = time.monotonic() + cls.ONVIF_DISCOVERY_TIMEOUT_SECONDS
            while len(devices) < 32:
                remaining = end_time - time.monotonic()
                if remaining <= 0:
                    break
                probe_socket.settimeout(remaining)
                try:
                    payload, sender = probe_socket.recvfrom(65535)
                except socket.timeout:
                    break

                try:
                    root = element_tree.fromstring(payload)
                except element_tree.ParseError:
                    continue

                addresses = []
                scopes = ""
                for element in root.iter():
                    if element.tag.endswith("XAddrs") and element.text:
                        addresses.extend(element.text.split())
                    elif element.tag.endswith("Scopes") and element.text:
                        scopes = element.text

                for address in addresses:
                    try:
                        parsed = urlparse(address)
                        host = parsed.hostname or sender[0]
                        port = parsed.port or (
                            443 if parsed.scheme.lower() == "https" else 80
                        )
                    except ValueError:
                        continue
                    if parsed.scheme.lower() not in {"http", "https"}:
                        continue
                    key = (host, port)
                    if key in devices:
                        continue

                    scope_name = ""
                    for scope in scopes.split():
                        decoded_scope = unquote(scope)
                        if "/name/" in decoded_scope.lower():
                            scope_name = decoded_scope.rsplit("/", 1)[-1]
                            break

                    devices[key] = {
                        "host": host,
                        "port": port,
                        "device_service_url": address,
                        "name": scope_name or f"ONVIF camera ({host})",
                    }
        except OSError as exc:
            return {
                    "devices": list(devices.values()),
                    "message": f"ONVIF discovery could not access the local network: {exc}",
            }
        finally:
            if probe_socket is not None:
                probe_socket.close()

        found = list(devices.values())
        return {
            "devices": found,
            "message": (
                f"Found {len(found)} ONVIF camera(s)."
                if found
                else (
                    "No ONVIF cameras replied. Check that the camera and "
                    "VisionX PC are on the same LAN and ONVIF is enabled."
                )
            ),
        }

    def test(self, request: CameraConnectionRequest):
        camera_type = request.camera_type.upper()
        if camera_type in {"LOCAL", "USB", "WEBCAM"}:
            if request.stream_url.strip():
                parsed = urlparse(request.stream_url.strip())
                if parsed.scheme.lower() != "local":
                    return self._failure(
                        "INVALID_URL",
                        "Local cameras must use a local://<device-index> source.",
                    )
                device_index = parsed.netloc
            else:
                device_index = request.device_index
                if device_index is None or str(device_index).strip() == "":
                    device_index = request.host or 0
            return self._validate_local_camera(device_index)
        if request.stream_url.strip():
            stream_url = request.stream_url.strip()
            parsed = urlparse(stream_url)
            if not parsed.username:
                stream_url = self._with_credentials(
                    stream_url,
                    request.username,
                    request.password,
                )
            return self._validate_stream(stream_url)

        host = request.host.strip()
        if not host:
            return self._failure("INVALID_URL", "Camera IP/host is required.")
        try:
            request.port = (
                int(request.port)
                if request.port is not None and str(request.port).strip()
                else None
            )
        except (TypeError, ValueError):
            return self._failure("INVALID_PORT", "Camera port must be a number.")
        if request.port is not None and not 1 <= request.port <= 65535:
            return self._failure(
                "INVALID_PORT",
                "Camera port must be between 1 and 65535.",
            )

        if camera_type in {"ONVIF", "OTHER"}:
            onvif_result = self._discover_onvif(request)
            if onvif_result["success"]:
                return onvif_result

        port = request.port or self.RTSP_PORT
        if (
            camera_type in {"ONVIF", "OTHER"}
            and port in self.ONVIF_PORTS
        ):
            port = self.RTSP_PORT
        if not self._port_open(host, port):
            return self._failure("PORT_CLOSED", "Camera IP is unreachable or RTSP port is closed.", reachable=False, protocol="rtsp", host=host, port=port)

        paths = [request.stream_path.strip()] if request.stream_path.strip() else []
        paths.extend(path for path in self.RTSP_PATHS if path not in paths)
        last_result = None
        for path in paths:
            result = self._validate_stream(self._build_rtsp_url(host, port, path, request.username, request.password))
            last_result = result
            if result["success"]:
                return result
        return last_result or self._failure("STREAM_NOT_FOUND", "RTSP stream could not be detected.", reachable=True)

    def _validate_local_camera(self, device_index):
        try:
            device_index = int(device_index)
        except (TypeError, ValueError):
            return self._failure(
                "INVALID_DEVICE_INDEX",
                "Local camera device index must be a number.",
            )

        if not 0 <= device_index <= 255:
            return self._failure(
                "INVALID_DEVICE_INDEX",
                "Local camera device index must be between 0 and 255.",
            )

        from streaming.camera_stream_service import (
            CameraStream,
            CameraStreamError,
        )

        stream = CameraStream(
            source=device_index,
            reconnect_attempts=1,
            reconnect_delay=0,
        )
        try:
            stream.connect()
        except CameraStreamError:
            return self._failure(
                "DEVICE_NOT_FOUND",
                f"No local camera is available at device index {device_index}.",
            )

        try:
            frame = stream.read()
            properties = stream.get_properties()
        except CameraStreamError:
            return self._failure(
                "TIMEOUT",
                "The local camera opened but did not return a frame.",
                reachable=True,
            )
        finally:
            stream.release()

        if frame is None:
            return self._failure(
                "TIMEOUT",
                "The local camera opened but did not return a frame.",
                reachable=True,
            )

        return {
            "success": True,
            "reachable": True,
            "protocol": "local",
            "stream_url": f"local://{device_index}",
            "message": "Local camera connected successfully.",
            "fps": max(0, round(float(properties.get("fps") or 0), 2)),
            "width": int(properties.get("width") or 0),
            "height": int(properties.get("height") or 0),
        }

    def _discover_onvif(self, request: CameraConnectionRequest):
        host = request.host.strip()
        ports = [int(request.port)] if request.port else []
        ports.extend(port for port in self.ONVIF_PORTS if port not in ports)
        last_result = None
        for port in ports:
            try:
                from onvif import ONVIFCamera
                if not self._port_open(host, port):
                    continue
                camera = ONVIFCamera(host, port, request.username, request.password)
                media = camera.create_media_service()
                for profile in media.GetProfiles():
                    response = media.GetStreamUri({"StreamSetup": {"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}}, "ProfileToken": profile.token})
                    uri = getattr(response, "Uri", "")
                    if not uri:
                        continue
                    result = self._validate_stream(self._with_credentials(uri, request.username, request.password))
                    last_result = result
                    if result["success"]:
                        result.update({"protocol": "rtsp", "onvif_port": port, "message": "Camera connected successfully via ONVIF."})
                        return result
            except Exception as exc:
                message = str(exc).lower()
                auth_failed = any(value in message for value in ("auth", "401", "unauthorized"))
                last_result = self._failure("AUTH_FAILED" if auth_failed else "ONVIF_FAILED", "Camera authentication failed." if auth_failed else "ONVIF discovery failed.", reachable=True, protocol="onvif", host=host, port=port)
        return last_result or self._failure("ONVIF_UNAVAILABLE", "ONVIF service is unavailable.", reachable=False, protocol="onvif")

    def _validate_stream(self, stream_url):
        parsed = urlparse(stream_url)
        if parsed.scheme.lower() not in {"rtsp", "http", "https"} or not parsed.hostname:
            return self._failure("INVALID_URL", "Stream URL must include a valid protocol and host.")
        try:
            import cv2
            capture = cv2.VideoCapture(
                stream_url,
                cv2.CAP_FFMPEG,
                [
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                    5000,
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                    5000,
                ],
            )
            try:
                opened = capture.isOpened()
                ok, frame = capture.read() if opened else (False, None)
                fps = capture.get(cv2.CAP_PROP_FPS) if opened else 0
                width = capture.get(cv2.CAP_PROP_FRAME_WIDTH) if opened else 0
                height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT) if opened else 0
            finally:
                capture.release()
        except Exception:
            return self._failure("FAILED", "Camera connection test failed.", reachable=True)
        if not opened:
            return self._failure("STREAM_NOT_FOUND", "RTSP stream could not be opened.", reachable=True)
        if not ok or frame is None:
            return self._failure("TIMEOUT", "Camera is reachable but the stream did not return a frame.", reachable=True)
        return {"success": True, "reachable": True, "protocol": parsed.scheme.lower(), "stream_url": self._strip_credentials(stream_url), "message": "Camera connected successfully.", "fps": round(float(fps or 0), 2), "width": int(width or 0), "height": int(height or 0)}

    @staticmethod
    def _port_open(host, port):
        try:
            with socket.create_connection((host, int(port)), timeout=3):
                return True
        except OSError:
            return False

    @staticmethod
    def _failure(code, message, reachable=False, **extra):
        return {"success": False, "reachable": reachable, "error_code": code, "message": message, **extra}

    @staticmethod
    def _build_rtsp_url(host, port, path, username, password):
        credential = quote(username, safe="")
        if credential and password:
            credential += ":" + quote(password, safe="")
        if credential:
            credential += "@"
        return f"rtsp://{credential}{host}:{port}/{path.lstrip('/')}"

    @staticmethod
    def _with_credentials(stream_url, username, password):
        parsed = urlparse(stream_url)
        if not username or not parsed.hostname or parsed.username:
            return stream_url
        credentials = quote(username, safe="")
        if password:
            credentials += ":" + quote(password, safe="")
        netloc = f"{credentials}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

    @staticmethod
    def _strip_credentials(stream_url):
        parsed = urlparse(stream_url)
        if not parsed.hostname:
            return stream_url
        netloc = parsed.hostname
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


camera_connection_discovery_service = CameraConnectionDiscoveryService()
