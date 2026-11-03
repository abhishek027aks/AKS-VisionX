import socket
import cv2
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from .connection_discovery import (
    CameraConnectionDiscoveryService,
    CameraConnectionRequest,
)


class CameraConnectionDiscoveryTests(SimpleTestCase):
    def test_local_discovery_returns_only_working_device_indexes(self):
        service = CameraConnectionDiscoveryService()

        def result_for(index):
            if index in (0, 3):
                return {
                    "success": True,
                    "stream_url": f"local://{index}",
                    "width": 640,
                    "height": 480,
                    "fps": 30,
                }
            return {
                "success": False,
                "error_code": "DEVICE_NOT_FOUND",
                "message": "Device unavailable.",
            }

        with patch.object(
            CameraConnectionDiscoveryService,
            "LOCAL_CAMERA_SCAN_LIMIT",
            4,
        ), patch.object(
            CameraConnectionDiscoveryService,
            "_validate_local_camera",
            side_effect=result_for,
        ):
            result = service.discover_local_cameras()

        self.assertEqual(
            [device["device_index"] for device in result["devices"]],
            [0, 3],
        )

    @patch("cameras.connection_discovery.socket.socket")
    def test_onvif_discovery_parses_device_address_and_name(
        self,
        socket_factory,
    ):
        response = b"""<e:Envelope xmlns:e="urn:soap" xmlns:d="urn:discovery">
          <e:Body><d:ProbeMatch>
            <d:XAddrs>http://192.0.2.40:8080/onvif/device_service</d:XAddrs>
            <d:Scopes>onvif://www.onvif.org/name/Front%20Door</d:Scopes>
          </d:ProbeMatch></e:Body>
        </e:Envelope>"""
        probe_socket = MagicMock()
        probe_socket.recvfrom.side_effect = [
            (response, ("192.0.2.40", 3702)),
            socket.timeout(),
        ]
        socket_factory.return_value = probe_socket

        result = CameraConnectionDiscoveryService.discover_onvif_devices()

        self.assertEqual(len(result["devices"]), 1)
        self.assertEqual(result["devices"][0]["host"], "192.0.2.40")
        self.assertEqual(result["devices"][0]["port"], 8080)
        self.assertEqual(result["devices"][0]["name"], "Front Door")
        probe_socket.close.assert_called_once()

    @patch("cameras.connection_discovery.socket.socket")
    def test_onvif_discovery_returns_empty_result_when_no_camera_replies(
        self,
        socket_factory,
    ):
        probe_socket = MagicMock()
        probe_socket.recvfrom.side_effect = socket.timeout()
        socket_factory.return_value = probe_socket

        result = CameraConnectionDiscoveryService.discover_onvif_devices()

        self.assertEqual(result["devices"], [])
        self.assertIn("No ONVIF cameras replied", result["message"])
        probe_socket.close.assert_called_once()

    @patch("cv2.VideoCapture")
    def test_local_camera_connection_returns_device_source(
        self,
        video_capture,
    ):
        capture = MagicMock()
        capture.isOpened.return_value = True
        capture.read.return_value = (True, object())
        capture.get.side_effect = [1280.0, 720.0, 25.0]
        video_capture.return_value = capture

        result = CameraConnectionDiscoveryService().test(
            CameraConnectionRequest(
                camera_type="LOCAL",
                device_index="1",
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["stream_url"], "local://1")
        self.assertEqual(result["width"], 1280)
        self.assertEqual(result["height"], 720)
        video_capture.assert_called_once_with(1, cv2.CAP_DSHOW)

    def test_local_camera_rejects_invalid_device_index(self):
        result = CameraConnectionDiscoveryService().test(
            CameraConnectionRequest(
                camera_type="LOCAL",
                device_index="-1",
            )
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "INVALID_DEVICE_INDEX")

    @patch("cv2.VideoCapture")
    def test_explicit_stream_url_uses_credentials_and_reports_metadata(
        self,
        video_capture,
    ):
        capture = MagicMock()
        capture.isOpened.return_value = True
        capture.read.return_value = (True, object())
        capture.get.side_effect = [25.0, 1920.0, 1080.0]
        video_capture.return_value = capture

        result = CameraConnectionDiscoveryService().test(
            CameraConnectionRequest(
                camera_type="RTSP",
                username="camera user",
                password="camera/password",
                stream_url="rtsp://192.0.2.15/live",
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["width"], 1920)
        self.assertEqual(result["height"], 1080)
        self.assertEqual(result["stream_url"], "rtsp://192.0.2.15/live")
        self.assertIn(
            "camera%20user:camera%2Fpassword@",
            video_capture.call_args.args[0],
        )

    def test_invalid_port_returns_error_without_probing(self):
        with patch("cameras.connection_discovery.socket.create_connection") as connect:
            result = CameraConnectionDiscoveryService().test(
                CameraConnectionRequest(
                    camera_type="RTSP",
                    host="192.0.2.15",
                    port=70000,
                )
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "INVALID_PORT")
        connect.assert_not_called()
