from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase

from accounts.models import Organization
from events.models import (
    Detection,
    TrackingPoint,
    TrackingLocation,
    TrackingCameraVisit,
    Event,
)
from audit.models import AuditLog

from .permissions import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_SUPER_ADMIN,
    ROLE_VIEWER,
    HasOrganization,
    IsAdminOrSuperAdmin,
    IsOperatorOrAbove,
    IsOrganizationAdminOrSuperAdmin,
    IsOrganizationOperatorOrAbove,
    IsOrganizationViewerOrAbove,
    IsSuperAdmin,
    IsViewerOrAbove,
    get_user_organization,
    has_any_role,
    has_role,
    is_super_admin,
)


User = get_user_model()


class RBACPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(name="RBAC Test Organization")
        cls.super_admin_group = Group.objects.create(name=ROLE_SUPER_ADMIN)
        cls.admin_group = Group.objects.create(name=ROLE_ADMIN)
        cls.operator_group = Group.objects.create(name=ROLE_OPERATOR)
        cls.viewer_group = Group.objects.create(name=ROLE_VIEWER)

        cls.super_admin = User.objects.create_user(
            username="test_super_admin",
            password="TestPass123!",
            is_active=True,
        )

        cls.admin = User.objects.create_user(
            username="test_admin",
            password="TestPass123!",
            is_active=True,
        )

        cls.operator = User.objects.create_user(
            username="test_operator",
            password="TestPass123!",
            is_active=True,
        )

        cls.viewer = User.objects.create_user(
            username="test_viewer",
            password="TestPass123!",
            is_active=True,
        )

        cls.no_role = User.objects.create_user(
            username="test_no_role",
            password="TestPass123!",
            is_active=True,
        )

        cls.inactive_viewer = User.objects.create_user(
            username="test_inactive_viewer",
            password="TestPass123!",
            is_active=False,
        )

        cls.super_admin.groups.add(cls.super_admin_group)
        cls.admin.groups.add(cls.admin_group)
        cls.operator.groups.add(cls.operator_group)
        cls.viewer.groups.add(cls.viewer_group)
        cls.inactive_viewer.groups.add(cls.viewer_group)

        cls.factory = RequestFactory()

    def request_for(self, user):
        request = self.factory.get("/test/")
        request.user = user
        return request

    def test_has_role(self):
        self.assertTrue(has_role(self.viewer, ROLE_VIEWER))
        self.assertFalse(has_role(self.viewer, ROLE_ADMIN))
        self.assertFalse(has_role(self.no_role, ROLE_VIEWER))

    def test_has_any_role(self):
        self.assertTrue(
            has_any_role(
                self.viewer,
                [ROLE_VIEWER, ROLE_OPERATOR],
            )
        )
        self.assertFalse(
            has_any_role(
                self.viewer,
                [ROLE_ADMIN, ROLE_SUPER_ADMIN],
            )
        )

    def test_super_admin_detection(self):
        self.assertTrue(is_super_admin(self.super_admin))
        self.assertFalse(is_super_admin(self.admin))

    def test_unauthenticated_user_has_no_role(self):
        request = self.factory.get("/test/")
        request.user = None

        self.assertFalse(has_role(None, ROLE_VIEWER))
        self.assertFalse(has_any_role(None, [ROLE_VIEWER]))
        self.assertFalse(is_super_admin(None))

    def test_is_super_admin_permission(self):
        permission = IsSuperAdmin()

        self.assertTrue(
            permission.has_permission(
                self.request_for(self.super_admin),
                None,
            )
        )
        self.assertFalse(
            permission.has_permission(
                self.request_for(self.admin),
                None,
            )
        )

    def test_admin_or_super_admin_permission(self):
        permission = IsAdminOrSuperAdmin()

        self.assertTrue(
            permission.has_permission(
                self.request_for(self.super_admin),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.admin),
                None,
            )
        )
        self.assertFalse(
            permission.has_permission(
                self.request_for(self.operator),
                None,
            )
        )
        self.assertFalse(
            permission.has_permission(
                self.request_for(self.viewer),
                None,
            )
        )

    def test_operator_or_above_permission(self):
        permission = IsOperatorOrAbove()

        self.assertTrue(
            permission.has_permission(
                self.request_for(self.super_admin),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.admin),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.operator),
                None,
            )
        )
        self.assertFalse(
            permission.has_permission(
                self.request_for(self.viewer),
                None,
            )
        )

    def test_viewer_or_above_permission(self):
        permission = IsViewerOrAbove()

        self.assertTrue(
            permission.has_permission(
                self.request_for(self.super_admin),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.admin),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.operator),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.viewer),
                None,
            )
        )
        self.assertFalse(
            permission.has_permission(
                self.request_for(self.no_role),
                None,
            )
        )

    def test_has_organization(self):
        permission = HasOrganization()

        self.viewer.organization = self.organization
        self.viewer.save(update_fields=["organization"])

        self.assertTrue(
            permission.has_permission(
                self.request_for(self.viewer),
                None,
            )
        )

        self.assertTrue(
            permission.has_permission(
                self.request_for(self.super_admin),
                None,
            )
        )

        self.assertFalse(
            permission.has_permission(
                self.request_for(self.no_role),
                None,
            )
        )

    def test_organization_admin_or_super_admin(self):
        permission = IsOrganizationAdminOrSuperAdmin()

        self.admin.organization = self.organization
        self.admin.save(update_fields=["organization"])

        self.assertTrue(
            permission.has_permission(
                self.request_for(self.admin),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.super_admin),
                None,
            )
        )
        self.assertFalse(
            permission.has_permission(
                self.request_for(self.operator),
                None,
            )
        )

        self.operator.organization = self.organization
        self.operator.save(update_fields=["organization"])

        self.assertFalse(
            permission.has_permission(
                self.request_for(self.operator),
                None,
            )
        )

    def test_organization_operator_or_above(self):
        permission = IsOrganizationOperatorOrAbove()

        self.admin.organization = self.organization
        self.admin.save(update_fields=["organization"])

        self.operator.organization = self.organization
        self.operator.save(update_fields=["organization"])

        self.assertTrue(
            permission.has_permission(
                self.request_for(self.admin),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.operator),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.super_admin),
                None,
            )
        )
        self.assertFalse(
            permission.has_permission(
                self.request_for(self.viewer),
                None,
            )
        )

    def test_organization_viewer_or_above(self):
        permission = IsOrganizationViewerOrAbove()

        self.admin.organization = self.organization
        self.admin.save(update_fields=["organization"])

        self.operator.organization = self.organization
        self.operator.save(update_fields=["organization"])

        self.viewer.organization = self.organization
        self.viewer.save(update_fields=["organization"])

        self.assertTrue(
            permission.has_permission(
                self.request_for(self.admin),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.operator),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.viewer),
                None,
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.request_for(self.super_admin),
                None,
            )
        )

        self.assertFalse(
            permission.has_permission(
                self.request_for(self.no_role),
                None,
            )
        )

    def test_get_user_organization(self):
        self.assertIsNone(
            get_user_organization(self.super_admin)
        )

        self.viewer.organization = self.organization
        self.viewer.save(update_fields=["organization"])

        self.assertEqual(
            get_user_organization(self.viewer).pk,
            self.organization.pk,
        )


from rest_framework.test import APIClient


class AuthenticationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Authentication Test Organization"
        )

        cls.viewer_group = Group.objects.create(name=ROLE_VIEWER)

        cls.user = User.objects.create_user(
            username="auth_test_user",
            password="AuthTestPass123!",
            email="auth@test.local",
            is_active=True,
        )
        cls.user.organization = cls.organization
        cls.user.save(update_fields=["organization"])
        cls.user.groups.add(cls.viewer_group)

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def login(self, password="AuthTestPass123!"):
        return self.client.post(
            "/api/auth/token/",
            {
                "username": "auth_test_user",
                "password": password,
            },
            format="json",
        )

    def test_login_success(self):
        before = AuditLog.objects.filter(
            action=AuditLog.Action.LOGIN,
            result=AuditLog.Result.SUCCESS,
            user=self.user,
        ).count()

        response = self.login()

        after = AuditLog.objects.filter(
            action=AuditLog.Action.LOGIN,
            result=AuditLog.Result.SUCCESS,
            user=self.user,
        ).count()

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(after, before + 1)

    def test_failed_login_creates_audit_log(self):
        before = AuditLog.objects.filter(
            action=AuditLog.Action.LOGIN,
            result=AuditLog.Result.FAILURE,
        ).count()

        response = self.login(password="WrongPassword999!")

        after = AuditLog.objects.filter(
            action=AuditLog.Action.LOGIN,
            result=AuditLog.Result.FAILURE,
        ).count()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(after, before + 1)

        log = AuditLog.objects.filter(
            action=AuditLog.Action.LOGIN,
            result=AuditLog.Result.FAILURE,
        ).order_by("-created_at").first()

        self.assertIsNotNone(log)
        self.assertIsNone(log.user)
        self.assertEqual(
            log.metadata.get("username"),
            "auth_test_user",
        )

    def test_me_requires_authentication(self):
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 401)

    def test_me_returns_current_user(self):
        login = self.login()

        self.assertEqual(login.status_code, 200)

        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + login.data["access"]
        )

        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["username"],
            "auth_test_user",
        )

    def test_logout_blacklists_refresh_token_and_creates_audit(self):
        login = self.login()

        self.assertEqual(login.status_code, 200)

        access = login.data["access"]
        refresh = login.data["refresh"]

        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + access
        )

        before = AuditLog.objects.filter(
            action=AuditLog.Action.LOGOUT,
            result=AuditLog.Result.SUCCESS,
            user=self.user,
        ).count()

        response = self.client.post(
            "/api/auth/logout/",
            {"refresh": refresh},
            format="json",
        )

        after = AuditLog.objects.filter(
            action=AuditLog.Action.LOGOUT,
            result=AuditLog.Result.SUCCESS,
            user=self.user,
        ).count()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(after, before + 1)

        refresh_response = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )

        self.assertEqual(refresh_response.status_code, 401)

    def test_logout_requires_refresh_token(self):
        login = self.login()

        self.assertEqual(login.status_code, 200)

        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + login.data["access"]
        )

        response = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_password_change_requires_authentication(self):
        response = self.client.post(
            "/api/auth/change-password/",
            {
                "old_password": "AuthTestPass123!",
                "new_password": "NewAuthPass456!",
                "new_password_confirm": "NewAuthPass456!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_password_change_success(self):
        login = self.login()

        self.assertEqual(login.status_code, 200)

        access = login.data["access"]
        refresh = login.data["refresh"]

        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + access
        )

        before = AuditLog.objects.filter(
            action=AuditLog.Action.PASSWORD_CHANGED,
            result=AuditLog.Result.SUCCESS,
            user=self.user,
        ).count()

        response = self.client.post(
            "/api/auth/change-password/",
            {
                "old_password": "AuthTestPass123!",
                "new_password": "NewAuthPass456!",
                "new_password_confirm": "NewAuthPass456!",
            },
            format="json",
        )

        after = AuditLog.objects.filter(
            action=AuditLog.Action.PASSWORD_CHANGED,
            result=AuditLog.Result.SUCCESS,
            user=self.user,
        ).count()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(after, before + 1)

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password("NewAuthPass456!")
        )

        old_refresh_response = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )

        self.assertEqual(old_refresh_response.status_code, 401)

    def test_password_change_rejects_wrong_current_password(self):
        login = self.login()

        self.assertEqual(login.status_code, 200)

        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + login.data["access"]
        )

        response = self.client.post(
            "/api/auth/change-password/",
            {
                "old_password": "WrongCurrentPassword!",
                "new_password": "NewAuthPass456!",
                "new_password_confirm": "NewAuthPass456!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("old_password", response.data)

    def test_password_change_rejects_mismatched_passwords(self):
        login = self.login()

        self.assertEqual(login.status_code, 200)

        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + login.data["access"]
        )

        response = self.client.post(
            "/api/auth/change-password/",
            {
                "old_password": "AuthTestPass123!",
                "new_password": "NewAuthPass456!",
                "new_password_confirm": "DifferentPass789!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "new_password_confirm",
            response.data,
        )

from cameras.models import Camera, CameraStream
from events.identity_models import PersonProfile, VehicleProfile
from events.identity_match_models import IdentityMatch
from events.tracking_models import TrackingSession
from recordings.models import Recording
from django.utils import timezone


class CameraAPIAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(
            name="Camera API Isolation Organization A",
            slug="camera-api-isolation-org-a",
        )

        cls.org_b = Organization.objects.create(
            name="Camera API Isolation Organization B",
            slug="camera-api-isolation-org-b",
        )

        cls.viewer_group = Group.objects.create(
            name=ROLE_VIEWER
        )
        cls.operator_group = Group.objects.create(
            name=ROLE_OPERATOR
        )
        cls.admin_group = Group.objects.create(
            name=ROLE_ADMIN
        )

        cls.viewer = User.objects.create_user(
            username="camera_viewer",
            password="CameraTestPass123!",
            is_active=True,
        )
        cls.viewer.organization = cls.org_a
        cls.viewer.save(update_fields=["organization"])
        cls.viewer.groups.add(cls.viewer_group)

        cls.operator = User.objects.create_user(
            username="camera_operator",
            password="CameraTestPass123!",
            is_active=True,
        )
        cls.operator.organization = cls.org_a
        cls.operator.save(update_fields=["organization"])
        cls.operator.groups.add(cls.operator_group)

        cls.admin = User.objects.create_user(
            username="camera_admin",
            password="CameraTestPass123!",
            is_active=True,
        )
        cls.admin.organization = cls.org_a
        cls.admin.save(update_fields=["organization"])
        cls.admin.groups.add(cls.admin_group)

        cls.other_viewer = User.objects.create_user(
            username="camera_other_viewer",
            password="CameraTestPass123!",
            is_active=True,
        )
        cls.other_viewer.organization = cls.org_b
        cls.other_viewer.save(update_fields=["organization"])
        cls.other_viewer.groups.add(cls.viewer_group)

        cls.camera_a = Camera.objects.create(
            organization=cls.org_a,
            created_by=cls.operator,
            name="Camera A",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.1.10",
        )

        cls.camera_b = Camera.objects.create(
            organization=cls.org_b,
            created_by=cls.other_viewer,
            name="Camera B",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.2.10",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_viewer_can_list_cameras(self):
        self.authenticate(self.viewer)
        response = self.client.get("/api/cameras/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}
        self.assertIn(self.camera_a.id, ids)
        self.assertNotIn(self.camera_b.id, ids)

    def test_viewer_can_retrieve_own_organization_camera(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/cameras/{self.camera_a.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.camera_a.id)

    def test_viewer_cannot_retrieve_other_organization_camera(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/cameras/{self.camera_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_viewer_cannot_create_camera(self):
        self.authenticate(self.viewer)

        response = self.client.post(
            "/api/cameras/",
            {
                "name": "Viewer Camera",
                "connection_type": "RTSP",
                "host": "10.0.0.10",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_operator_can_create_camera(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/cameras/",
            {
                "name": "Operator Camera",
                "connection_type": "RTSP",
                "host": "10.0.0.20",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["organization"], self.org_a.id)
        self.assertEqual(response.data["created_by"], self.operator.id)

    def test_operator_can_update_own_organization_camera(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/cameras/{self.camera_a.id}/",
            {"name": "Camera A Updated"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.camera_a.refresh_from_db()
        self.assertEqual(self.camera_a.name, "Camera A Updated")

    def test_operator_cannot_update_other_organization_camera(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/cameras/{self.camera_b.id}/",
            {"name": "Hacked Camera"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.camera_b.refresh_from_db()
        self.assertEqual(self.camera_b.name, "Camera B")

    def test_operator_can_delete_camera(self):
        self.authenticate(self.operator)

        response = self.client.delete(
            f"/api/cameras/{self.camera_a.id}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Camera.objects.filter(pk=self.camera_a.id).exists()
        )

    def test_admin_can_delete_own_organization_camera(self):
        self.authenticate(self.admin)

        camera = Camera.objects.create(
            organization=self.org_a,
            created_by=self.operator,
            name="Admin Delete Camera",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.1.30",
        )

        response = self.client.delete(
            f"/api/cameras/{camera.id}/"
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            Camera.objects.filter(pk=camera.id).exists()
        )

    def test_admin_cannot_delete_other_organization_camera(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            f"/api/cameras/{self.camera_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Camera.objects.filter(pk=self.camera_b.id).exists()
        )

    def test_other_organization_viewer_sees_only_own_camera(self):
        self.authenticate(self.other_viewer)

        response = self.client.get("/api/cameras/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertNotIn(self.camera_a.id, ids)
        self.assertIn(self.camera_b.id, ids)


class CameraStreamAPIAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(
            name="Stream API Isolation Organization A",
            slug="stream-api-isolation-org-a",
        )

        cls.org_b = Organization.objects.create(
            name="Stream API Isolation Organization B",
            slug="stream-api-isolation-org-b",
        )

        cls.viewer_group = Group.objects.create(
            name=ROLE_VIEWER
        )
        cls.operator_group = Group.objects.create(
            name=ROLE_OPERATOR
        )
        cls.admin_group = Group.objects.create(
            name=ROLE_ADMIN
        )

        cls.viewer = User.objects.create_user(
            username="stream_viewer",
            password="StreamTestPass123!",
            is_active=True,
        )
        cls.viewer.organization = cls.org_a
        cls.viewer.save(update_fields=["organization"])
        cls.viewer.groups.add(cls.viewer_group)

        cls.operator = User.objects.create_user(
            username="stream_operator",
            password="StreamTestPass123!",
            is_active=True,
        )
        cls.operator.organization = cls.org_a
        cls.operator.save(update_fields=["organization"])
        cls.operator.groups.add(cls.operator_group)

        cls.admin = User.objects.create_user(
            username="stream_admin",
            password="StreamTestPass123!",
            is_active=True,
        )
        cls.admin.organization = cls.org_a
        cls.admin.save(update_fields=["organization"])
        cls.admin.groups.add(cls.admin_group)

        cls.other_viewer = User.objects.create_user(
            username="stream_other_viewer",
            password="StreamTestPass123!",
            is_active=True,
        )
        cls.other_viewer.organization = cls.org_b
        cls.other_viewer.save(update_fields=["organization"])
        cls.other_viewer.groups.add(cls.viewer_group)

        cls.camera_a = Camera.objects.create(
            organization=cls.org_a,
            created_by=cls.operator,
            name="Stream Camera A",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.10.10",
        )

        cls.camera_b = Camera.objects.create(
            organization=cls.org_b,
            created_by=cls.other_viewer,
            name="Stream Camera B",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.20.10",
        )

        cls.stream_a = CameraStream.objects.create(
            camera=cls.camera_a,
            name="Main Stream A",
            stream_type=CameraStream.StreamType.MAIN,
            protocol=CameraStream.Protocol.RTSP,
            url="rtsp://192.168.10.10/main",
        )

        cls.stream_b = CameraStream.objects.create(
            camera=cls.camera_b,
            name="Main Stream B",
            stream_type=CameraStream.StreamType.MAIN,
            protocol=CameraStream.Protocol.RTSP,
            url="rtsp://192.168.20.10/main",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def stream_payload(self, camera_id, name="Test Stream"):
        return {
            "camera": camera_id,
            "name": name,
            "stream_type": "MAIN",
            "protocol": "RTSP",
            "url": "rtsp://10.10.10.10/test",
        }

    def test_viewer_can_list_own_organization_streams(self):
        self.authenticate(self.viewer)

        response = self.client.get("/api/streams/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertIn(self.stream_a.id, ids)
        self.assertNotIn(self.stream_b.id, ids)

    def test_viewer_can_retrieve_own_organization_stream(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/streams/{self.stream_a.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["id"],
            self.stream_a.id,
        )

    def test_viewer_cannot_retrieve_other_organization_stream(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/streams/{self.stream_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_viewer_cannot_create_stream(self):
        self.authenticate(self.viewer)

        response = self.client.post(
            "/api/streams/",
            self.stream_payload(
                self.camera_a.id,
                "Viewer Stream",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_operator_can_create_stream(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/streams/",
            self.stream_payload(
                self.camera_a.id,
                "Operator Stream",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["camera"],
            self.camera_a.id,
        )

        self.assertTrue(
            CameraStream.objects.filter(
                pk=response.data["id"],
                camera=self.camera_a,
            ).exists()
        )

    def test_operator_can_update_own_organization_stream(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/streams/{self.stream_a.id}/",
            {
                "name": "Updated Main Stream A",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.stream_a.refresh_from_db()

        self.assertEqual(
            self.stream_a.name,
            "Updated Main Stream A",
        )

    def test_operator_cannot_access_other_organization_stream(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/streams/{self.stream_b.id}/",
            {
                "name": "Hacked Stream",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.stream_b.refresh_from_db()

        self.assertEqual(
            self.stream_b.name,
            "Main Stream B",
        )

    def test_operator_cannot_delete_stream(self):
        self.authenticate(self.operator)

        response = self.client.delete(
            f"/api/streams/{self.stream_a.id}/"
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            CameraStream.objects.filter(
                pk=self.stream_a.id
            ).exists()
        )

    def test_admin_can_delete_own_organization_stream(self):
        self.authenticate(self.admin)

        stream = CameraStream.objects.create(
            camera=self.camera_a,
            name="Admin Delete Stream",
            stream_type=CameraStream.StreamType.SUB,
            protocol=CameraStream.Protocol.RTSP,
            url="rtsp://192.168.10.10/sub",
        )

        response = self.client.delete(
            f"/api/streams/{stream.id}/"
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            CameraStream.objects.filter(
                pk=stream.id
            ).exists()
        )

    def test_admin_cannot_delete_other_organization_stream(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            f"/api/streams/{self.stream_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            CameraStream.objects.filter(
                pk=self.stream_b.id
            ).exists()
        )

    def test_operator_cannot_create_stream_for_other_organization_camera(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/streams/",
            self.stream_payload(
                self.camera_b.id,
                "Cross Organization Stream",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(
            CameraStream.objects.filter(
                name="Cross Organization Stream"
            ).exists()
        )

    def test_other_organization_viewer_sees_only_own_streams(self):
        self.authenticate(self.other_viewer)

        response = self.client.get("/api/streams/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertNotIn(self.stream_a.id, ids)
        self.assertIn(self.stream_b.id, ids)


class ProfileAPIAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(
            name="Profile API Isolation Organization A",
            slug="profile-api-isolation-org-a",
        )

        cls.org_b = Organization.objects.create(
            name="Profile API Isolation Organization B",
            slug="profile-api-isolation-org-b",
        )

        cls.viewer_group = Group.objects.create(
            name=ROLE_VIEWER
        )
        cls.operator_group = Group.objects.create(
            name=ROLE_OPERATOR
        )
        cls.admin_group = Group.objects.create(
            name=ROLE_ADMIN
        )

        cls.viewer = User.objects.create_user(
            username="profile_viewer",
            password="ProfileTestPass123!",
            is_active=True,
        )
        cls.viewer.organization = cls.org_a
        cls.viewer.save(update_fields=["organization"])
        cls.viewer.groups.add(cls.viewer_group)

        cls.operator = User.objects.create_user(
            username="profile_operator",
            password="ProfileTestPass123!",
            is_active=True,
        )
        cls.operator.organization = cls.org_a
        cls.operator.save(update_fields=["organization"])
        cls.operator.groups.add(cls.operator_group)

        cls.admin = User.objects.create_user(
            username="profile_admin",
            password="ProfileTestPass123!",
            is_active=True,
        )
        cls.admin.organization = cls.org_a
        cls.admin.save(update_fields=["organization"])
        cls.admin.groups.add(cls.admin_group)

        cls.other_viewer = User.objects.create_user(
            username="profile_other_viewer",
            password="ProfileTestPass123!",
            is_active=True,
        )
        cls.other_viewer.organization = cls.org_b
        cls.other_viewer.save(update_fields=["organization"])
        cls.other_viewer.groups.add(cls.viewer_group)

        cls.person_a = PersonProfile.objects.create(
            organization=cls.org_a,
            name="Person A",
            category=PersonProfile.Category.EMPLOYEE,
            is_known=True,
            is_active=True,
        )

        cls.person_b = PersonProfile.objects.create(
            organization=cls.org_b,
            name="Person B",
            category=PersonProfile.Category.VISITOR,
            is_known=True,
            is_active=True,
        )

        cls.vehicle_a = VehicleProfile.objects.create(
            organization=cls.org_a,
            name="Vehicle A",
            category=VehicleProfile.Category.EMPLOYEE,
            vehicle_type=VehicleProfile.VehicleType.CAR,
            registration_number="UP01AB1234",
            is_known=True,
            is_active=True,
        )

        cls.vehicle_b = VehicleProfile.objects.create(
            organization=cls.org_b,
            name="Vehicle B",
            category=VehicleProfile.Category.VISITOR,
            vehicle_type=VehicleProfile.VehicleType.MOTORCYCLE,
            registration_number="UP02CD5678",
            is_known=True,
            is_active=True,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_viewer_can_list_own_person_profiles(self):
        self.authenticate(self.viewer)

        response = self.client.get("/api/persons/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertIn(self.person_a.id, ids)
        self.assertNotIn(self.person_b.id, ids)

    def test_viewer_can_retrieve_own_person_profile(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/persons/{self.person_a.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["id"],
            self.person_a.id,
        )

    def test_viewer_cannot_retrieve_other_organization_person(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/persons/{self.person_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_viewer_cannot_create_person_profile(self):
        self.authenticate(self.viewer)

        response = self.client.post(
            "/api/persons/",
            {
                "name": "Viewer Person",
                "category": "VISITOR",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_operator_can_create_person_profile(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/persons/",
            {
                "name": "Operator Person",
                "category": "EMPLOYEE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["organization"],
            self.org_a.id,
        )

        self.assertTrue(
            PersonProfile.objects.filter(
                pk=response.data["id"],
                organization=self.org_a,
            ).exists()
        )

    def test_operator_can_update_own_person_profile(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/persons/{self.person_a.id}/",
            {
                "name": "Person A Updated",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.person_a.refresh_from_db()

        self.assertEqual(
            self.person_a.name,
            "Person A Updated",
        )

    def test_operator_cannot_update_other_organization_person(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/persons/{self.person_b.id}/",
            {
                "name": "Hacked Person",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.person_b.refresh_from_db()

        self.assertEqual(
            self.person_b.name,
            "Person B",
        )

    def test_operator_cannot_delete_person_profile(self):
        self.authenticate(self.operator)

        response = self.client.delete(
            f"/api/persons/{self.person_a.id}/"
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            PersonProfile.objects.filter(
                pk=self.person_a.id
            ).exists()
        )

    def test_admin_can_delete_own_person_profile(self):
        self.authenticate(self.admin)

        person = PersonProfile.objects.create(
            organization=self.org_a,
            name="Admin Delete Person",
            category=PersonProfile.Category.OTHER,
        )

        response = self.client.delete(
            f"/api/persons/{person.id}/"
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            PersonProfile.objects.filter(
                pk=person.id
            ).exists()
        )

    def test_admin_cannot_delete_other_organization_person(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            f"/api/persons/{self.person_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            PersonProfile.objects.filter(
                pk=self.person_b.id
            ).exists()
        )

    def test_other_organization_viewer_sees_only_own_person_profiles(self):
        self.authenticate(self.other_viewer)

        response = self.client.get("/api/persons/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertNotIn(self.person_a.id, ids)
        self.assertIn(self.person_b.id, ids)

    def test_viewer_can_list_own_vehicle_profiles(self):
        self.authenticate(self.viewer)

        response = self.client.get("/api/vehicles/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertIn(self.vehicle_a.id, ids)
        self.assertNotIn(self.vehicle_b.id, ids)

    def test_viewer_can_retrieve_own_vehicle_profile(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/vehicles/{self.vehicle_a.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["id"],
            self.vehicle_a.id,
        )

    def test_viewer_cannot_retrieve_other_organization_vehicle(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/vehicles/{self.vehicle_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_viewer_cannot_create_vehicle_profile(self):
        self.authenticate(self.viewer)

        response = self.client.post(
            "/api/vehicles/",
            {
                "name": "Viewer Vehicle",
                "category": "VISITOR",
                "vehicle_type": "CAR",
                "registration_number": "UP03EF9999",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_operator_can_create_vehicle_profile(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/vehicles/",
            {
                "name": "Operator Vehicle",
                "category": "EMPLOYEE",
                "vehicle_type": "CAR",
                "registration_number": "UP04GH1111",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["organization"],
            self.org_a.id,
        )

        self.assertTrue(
            VehicleProfile.objects.filter(
                pk=response.data["id"],
                organization=self.org_a,
            ).exists()
        )

    def test_operator_can_update_own_vehicle_profile(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/vehicles/{self.vehicle_a.id}/",
            {
                "name": "Vehicle A Updated",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.vehicle_a.refresh_from_db()

        self.assertEqual(
            self.vehicle_a.name,
            "Vehicle A Updated",
        )

    def test_operator_cannot_update_other_organization_vehicle(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/vehicles/{self.vehicle_b.id}/",
            {
                "name": "Hacked Vehicle",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.vehicle_b.refresh_from_db()

        self.assertEqual(
            self.vehicle_b.name,
            "Vehicle B",
        )

    def test_operator_cannot_delete_vehicle_profile(self):
        self.authenticate(self.operator)

        response = self.client.delete(
            f"/api/vehicles/{self.vehicle_a.id}/"
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            VehicleProfile.objects.filter(
                pk=self.vehicle_a.id
            ).exists()
        )

    def test_admin_can_delete_own_vehicle_profile(self):
        self.authenticate(self.admin)

        vehicle = VehicleProfile.objects.create(
            organization=self.org_a,
            name="Admin Delete Vehicle",
            category=VehicleProfile.Category.OTHER,
            vehicle_type=VehicleProfile.VehicleType.CAR,
        )

        response = self.client.delete(
            f"/api/vehicles/{vehicle.id}/"
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            VehicleProfile.objects.filter(
                pk=vehicle.id
            ).exists()
        )

    def test_admin_cannot_delete_other_organization_vehicle(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            f"/api/vehicles/{self.vehicle_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            VehicleProfile.objects.filter(
                pk=self.vehicle_b.id
            ).exists()
        )

    def test_other_organization_viewer_sees_only_own_vehicle_profiles(self):
        self.authenticate(self.other_viewer)

        response = self.client.get("/api/vehicles/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertNotIn(self.vehicle_a.id, ids)
        self.assertIn(self.vehicle_b.id, ids)


class IdentityMatchAPIAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()

        cls.org_a = Organization.objects.create(
            name="Identity Match Isolation Organization A",
            slug="identity-match-isolation-org-a",
        )

        cls.org_b = Organization.objects.create(
            name="Identity Match Isolation Organization B",
            slug="identity-match-isolation-org-b",
        )

        cls.viewer_group = Group.objects.create(
            name=ROLE_VIEWER
        )
        cls.operator_group = Group.objects.create(
            name=ROLE_OPERATOR
        )
        cls.admin_group = Group.objects.create(
            name=ROLE_ADMIN
        )

        cls.viewer = User.objects.create_user(
            username="identity_viewer",
            password="IdentityTestPass123!",
            is_active=True,
        )
        cls.viewer.organization = cls.org_a
        cls.viewer.save(update_fields=["organization"])
        cls.viewer.groups.add(cls.viewer_group)

        cls.operator = User.objects.create_user(
            username="identity_operator",
            password="IdentityTestPass123!",
            is_active=True,
        )
        cls.operator.organization = cls.org_a
        cls.operator.save(update_fields=["organization"])
        cls.operator.groups.add(cls.operator_group)

        cls.admin = User.objects.create_user(
            username="identity_admin",
            password="IdentityTestPass123!",
            is_active=True,
        )
        cls.admin.organization = cls.org_a
        cls.admin.save(update_fields=["organization"])
        cls.admin.groups.add(cls.admin_group)

        cls.other_viewer = User.objects.create_user(
            username="identity_other_viewer",
            password="IdentityTestPass123!",
            is_active=True,
        )
        cls.other_viewer.organization = cls.org_b
        cls.other_viewer.save(update_fields=["organization"])
        cls.other_viewer.groups.add(cls.viewer_group)

        cls.camera_a = Camera.objects.create(
            organization=cls.org_a,
            created_by=cls.operator,
            name="Identity Camera A",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.30.10",
        )

        cls.camera_b = Camera.objects.create(
            organization=cls.org_b,
            created_by=cls.other_viewer,
            name="Identity Camera B",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.40.10",
        )

        cls.person_a = PersonProfile.objects.create(
            organization=cls.org_a,
            name="Identity Person A",
            category=PersonProfile.Category.EMPLOYEE,
        )

        cls.person_b = PersonProfile.objects.create(
            organization=cls.org_b,
            name="Identity Person B",
            category=PersonProfile.Category.VISITOR,
        )

        cls.vehicle_a = VehicleProfile.objects.create(
            organization=cls.org_a,
            name="Identity Vehicle A",
            category=VehicleProfile.Category.EMPLOYEE,
            vehicle_type=VehicleProfile.VehicleType.CAR,
            registration_number="UP11AA1111",
        )

        cls.vehicle_b = VehicleProfile.objects.create(
            organization=cls.org_b,
            name="Identity Vehicle B",
            category=VehicleProfile.Category.VISITOR,
            vehicle_type=VehicleProfile.VehicleType.CAR,
            registration_number="UP22BB2222",
        )

        cls.session_a = TrackingSession.objects.create(
            organization=cls.org_a,
            camera=cls.camera_a,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id="identity-track-a",
            person_profile=cls.person_a,
            label="Person A",
            status=TrackingSession.Status.ACTIVE,
            first_seen_at=now - timedelta(minutes=5),
            last_seen_at=now,
        )

        cls.session_b = TrackingSession.objects.create(
            organization=cls.org_b,
            camera=cls.camera_b,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id="identity-track-b",
            person_profile=cls.person_b,
            label="Person B",
            status=TrackingSession.Status.ACTIVE,
            first_seen_at=now - timedelta(minutes=5),
            last_seen_at=now,
        )

        cls.match_a = IdentityMatch.objects.create(
            organization=cls.org_a,
            tracking_session=cls.session_a,
            person_profile=cls.person_a,
            identity_type=IdentityMatch.IdentityType.PERSON,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=95.50,
            matched_at=now,
            is_confirmed=True,
        )

        cls.match_b = IdentityMatch.objects.create(
            organization=cls.org_b,
            tracking_session=cls.session_b,
            person_profile=cls.person_b,
            identity_type=IdentityMatch.IdentityType.PERSON,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=91.25,
            matched_at=now,
            is_confirmed=True,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_viewer_can_list_own_identity_matches(self):
        self.authenticate(self.viewer)

        response = self.client.get("/api/identity-matches/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertIn(self.match_a.id, ids)
        self.assertNotIn(self.match_b.id, ids)

    def test_viewer_can_retrieve_own_identity_match(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/identity-matches/{self.match_a.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["id"],
            self.match_a.id,
        )

    def test_viewer_cannot_retrieve_other_organization_match(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/identity-matches/{self.match_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_viewer_cannot_create_identity_match(self):
        self.authenticate(self.viewer)

        response = self.client.post(
            "/api/identity-matches/",
            {
                "tracking_session": self.session_a.id,
                "person_profile": self.person_a.id,
                "identity_type": "PERSON",
                "match_method": "MANUAL",
                "confidence": "88.00",
                "is_confirmed": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_operator_can_create_identity_match(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/identity-matches/",
            {
                "tracking_session": self.session_a.id,
                "person_profile": self.person_a.id,
                "identity_type": "PERSON",
                "match_method": "MANUAL",
                "confidence": "88.00",
                "is_confirmed": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["organization"],
            self.org_a.id,
        )
        self.assertEqual(
            response.data["tracking_session"],
            self.session_a.id,
        )

        self.assertTrue(
            IdentityMatch.objects.filter(
                pk=response.data["id"],
                organization=self.org_a,
            ).exists()
        )

    def test_operator_can_update_own_identity_match(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/identity-matches/{self.match_a.id}/",
            {
                "is_confirmed": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.match_a.refresh_from_db()

        self.assertFalse(self.match_a.is_confirmed)

    def test_operator_cannot_update_other_organization_match(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/identity-matches/{self.match_b.id}/",
            {
                "is_confirmed": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.match_b.refresh_from_db()

        self.assertTrue(self.match_b.is_confirmed)

    def test_operator_cannot_delete_identity_match(self):
        self.authenticate(self.operator)

        response = self.client.delete(
            f"/api/identity-matches/{self.match_a.id}/"
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            IdentityMatch.objects.filter(
                pk=self.match_a.id
            ).exists()
        )

    def test_admin_can_delete_own_identity_match(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            f"/api/identity-matches/{self.match_a.id}/"
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            IdentityMatch.objects.filter(
                pk=self.match_a.id
            ).exists()
        )

    def test_admin_cannot_delete_other_organization_match(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            f"/api/identity-matches/{self.match_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            IdentityMatch.objects.filter(
                pk=self.match_b.id
            ).exists()
        )

    def test_operator_cannot_create_match_for_other_organization_session(
        self,
    ):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/identity-matches/",
            {
                "tracking_session": self.session_b.id,
                "person_profile": self.person_b.id,
                "identity_type": "PERSON",
                "match_method": "MANUAL",
                "confidence": "80.00",
                "is_confirmed": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(
            IdentityMatch.objects.filter(
                tracking_session=self.session_b,
                match_method=IdentityMatch.MatchMethod.MANUAL,
            ).exists()
        )

    def test_operator_cannot_create_match_using_other_organization_person(
        self,
    ):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/identity-matches/",
            {
                "tracking_session": self.session_a.id,
                "person_profile": self.person_b.id,
                "identity_type": "PERSON",
                "match_method": "MANUAL",
                "confidence": "80.00",
                "is_confirmed": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_other_organization_viewer_sees_only_own_matches(self):
        self.authenticate(self.other_viewer)

        response = self.client.get("/api/identity-matches/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertNotIn(self.match_a.id, ids)
        self.assertIn(self.match_b.id, ids)



class EventAPIAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()

        cls.org_a = Organization.objects.create(
            name="Event API Isolation Organization A",
            slug="event-api-isolation-org-a",
        )

        cls.org_b = Organization.objects.create(
            name="Event API Isolation Organization B",
            slug="event-api-isolation-org-b",
        )

        cls.viewer_group = Group.objects.create(
            name=ROLE_VIEWER
        )
        cls.operator_group = Group.objects.create(
            name=ROLE_OPERATOR
        )
        cls.admin_group = Group.objects.create(
            name=ROLE_ADMIN
        )

        cls.viewer = User.objects.create_user(
            username="event_viewer",
            password="EventTestPass123!",
            is_active=True,
        )
        cls.viewer.organization = cls.org_a
        cls.viewer.save(update_fields=["organization"])
        cls.viewer.groups.add(cls.viewer_group)

        cls.operator = User.objects.create_user(
            username="event_operator",
            password="EventTestPass123!",
            is_active=True,
        )
        cls.operator.organization = cls.org_a
        cls.operator.save(update_fields=["organization"])
        cls.operator.groups.add(cls.operator_group)

        cls.admin = User.objects.create_user(
            username="event_admin",
            password="EventTestPass123!",
            is_active=True,
        )
        cls.admin.organization = cls.org_a
        cls.admin.save(update_fields=["organization"])
        cls.admin.groups.add(cls.admin_group)

        cls.other_viewer = User.objects.create_user(
            username="event_other_viewer",
            password="EventTestPass123!",
            is_active=True,
        )
        cls.other_viewer.organization = cls.org_b
        cls.other_viewer.save(update_fields=["organization"])
        cls.other_viewer.groups.add(cls.viewer_group)

        cls.camera_a = Camera.objects.create(
            organization=cls.org_a,
            created_by=cls.operator,
            name="Event Camera A",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.50.10",
        )

        cls.camera_b = Camera.objects.create(
            organization=cls.org_b,
            created_by=cls.other_viewer,
            name="Event Camera B",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.60.10",
        )

        cls.event_a = Event.objects.create(
            organization=cls.org_a,
            camera=cls.camera_a,
            event_type=Event.EventType.PERSON,
            status=Event.Status.NEW,
            title="Person Detected A",
            description="Organization A event",
            occurred_at=now,
            confidence=95.00,
        )

        cls.event_b = Event.objects.create(
            organization=cls.org_b,
            camera=cls.camera_b,
            event_type=Event.EventType.VEHICLE,
            status=Event.Status.NEW,
            title="Vehicle Detected B",
            description="Organization B event",
            occurred_at=now,
            confidence=91.00,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def event_payload(self, camera_id, title="Test Event"):
        return {
            "camera": camera_id,
            "event_type": "PERSON",
            "status": "NEW",
            "title": title,
            "description": "API authorization test event",
            "occurred_at": timezone.now().isoformat(),
            "confidence": "90.00",
            "protected": True,
            "metadata": {},
        }

    def test_viewer_can_list_own_organization_events(self):
        self.authenticate(self.viewer)

        response = self.client.get("/api/events/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertIn(self.event_a.id, ids)
        self.assertNotIn(self.event_b.id, ids)

    def test_viewer_can_retrieve_own_organization_event(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/events/{self.event_a.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.event_a.id)

    def test_viewer_cannot_retrieve_other_organization_event(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/events/{self.event_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_viewer_cannot_create_event(self):
        self.authenticate(self.viewer)

        response = self.client.post(
            "/api/events/",
            self.event_payload(
                self.camera_a.id,
                "Viewer Event",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_operator_can_create_event(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/events/",
            self.event_payload(
                self.camera_a.id,
                "Operator Event",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["organization"],
            self.org_a.id,
        )
        self.assertEqual(
            response.data["camera"],
            self.camera_a.id,
        )

        self.assertTrue(
            Event.objects.filter(
                pk=response.data["id"],
                organization=self.org_a,
            ).exists()
        )

    def test_operator_cannot_create_event_for_other_organization_camera(
        self,
    ):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/events/",
            self.event_payload(
                self.camera_b.id,
                "Cross Organization Event",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(
            Event.objects.filter(
                title="Cross Organization Event"
            ).exists()
        )

    def test_operator_can_update_own_organization_event(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/events/{self.event_a.id}/",
            {
                "title": "Updated Event A",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.event_a.refresh_from_db()

        self.assertEqual(
            self.event_a.title,
            "Updated Event A",
        )

    def test_operator_cannot_update_other_organization_event(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/events/{self.event_b.id}/",
            {
                "title": "Hacked Event",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.event_b.refresh_from_db()

        self.assertEqual(
            self.event_b.title,
            "Vehicle Detected B",
        )

    def test_operator_cannot_delete_event(self):
        self.authenticate(self.operator)

        response = self.client.delete(
            f"/api/events/{self.event_a.id}/"
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            Event.objects.filter(
                pk=self.event_a.id
            ).exists()
        )

    def test_admin_can_delete_own_organization_event(self):
        self.authenticate(self.admin)

        event = Event.objects.create(
            organization=self.org_a,
            camera=self.camera_a,
            event_type=Event.EventType.MOTION,
            status=Event.Status.NEW,
            title="Admin Delete Event",
            occurred_at=timezone.now(),
        )

        response = self.client.delete(
            f"/api/events/{event.id}/"
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            Event.objects.filter(
                pk=event.id
            ).exists()
        )

    def test_admin_cannot_delete_other_organization_event(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            f"/api/events/{self.event_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Event.objects.filter(
                pk=self.event_b.id
            ).exists()
        )

    def test_other_organization_viewer_sees_only_own_events(self):
        self.authenticate(self.other_viewer)

        response = self.client.get("/api/events/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertNotIn(self.event_a.id, ids)
        self.assertIn(self.event_b.id, ids)

    def test_event_status_new_to_acknowledged_is_allowed(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/events/{self.event_a.id}/",
            {
                "status": "ACKNOWLEDGED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.event_a.refresh_from_db()

        self.assertEqual(
            self.event_a.status,
            Event.Status.ACKNOWLEDGED,
        )

    def test_event_status_new_to_resolved_is_rejected(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/events/{self.event_a.id}/",
            {
                "status": "RESOLVED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.data)

        self.event_a.refresh_from_db()

        self.assertEqual(
            self.event_a.status,
            Event.Status.NEW,
        )

    def test_new_event_must_start_with_new_status(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/events/",
            {
                "camera": self.camera_a.id,
                "event_type": "PERSON",
                "status": "RESOLVED",
                "title": "Invalid Initial Status Event",
                "occurred_at": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.data)

    def test_event_filter_by_event_type_respects_organization_isolation(
        self,
    ):
        self.authenticate(self.viewer)

        response = self.client.get(
            "/api/events/?event_type=PERSON"
        )

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertIn(self.event_a.id, ids)
        self.assertNotIn(self.event_b.id, ids)

    def test_event_filter_by_status_respects_organization_isolation(
        self,
    ):
        self.authenticate(self.viewer)

        response = self.client.get(
            "/api/events/?status=NEW"
        )

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertIn(self.event_a.id, ids)
        self.assertNotIn(self.event_b.id, ids)

    def test_event_filter_by_camera_respects_organization_isolation(
        self,
    ):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/events/?camera={self.camera_b.id}"
        )

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertNotIn(self.event_b.id, ids)
        self.assertNotIn(self.event_a.id, ids)


class TrackingSessionSummaryAPIAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()

        cls.org_a = Organization.objects.create(
            name="Tracking Summary Isolation Organization A",
            slug="tracking-summary-isolation-org-a",
        )

        cls.org_b = Organization.objects.create(
            name="Tracking Summary Isolation Organization B",
            slug="tracking-summary-isolation-org-b",
        )

        cls.viewer_group = Group.objects.create(
            name=ROLE_VIEWER
        )

        cls.operator_group = Group.objects.create(
            name=ROLE_OPERATOR
        )

        cls.admin_group = Group.objects.create(
            name=ROLE_ADMIN
        )

        cls.viewer = User.objects.create_user(
            username="tracking_summary_viewer",
            password="TrackingSummaryTestPass123!",
            is_active=True,
        )
        cls.viewer.organization = cls.org_a
        cls.viewer.save(update_fields=["organization"])
        cls.viewer.groups.add(cls.viewer_group)

        cls.operator = User.objects.create_user(
            username="tracking_summary_operator",
            password="TrackingSummaryTestPass123!",
            is_active=True,
        )
        cls.operator.organization = cls.org_a
        cls.operator.save(update_fields=["organization"])
        cls.operator.groups.add(cls.operator_group)

        cls.admin = User.objects.create_user(
            username="tracking_summary_admin",
            password="TrackingSummaryTestPass123!",
            is_active=True,
        )
        cls.admin.organization = cls.org_a
        cls.admin.save(update_fields=["organization"])
        cls.admin.groups.add(cls.admin_group)

        cls.other_viewer = User.objects.create_user(
            username="tracking_summary_other_viewer",
            password="TrackingSummaryTestPass123!",
            is_active=True,
        )
        cls.other_viewer.organization = cls.org_b
        cls.other_viewer.save(update_fields=["organization"])
        cls.other_viewer.groups.add(cls.viewer_group)

        cls.camera_a = Camera.objects.create(
            organization=cls.org_a,
            created_by=cls.operator,
            name="Tracking Summary Camera A",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.70.10",
        )

        cls.camera_b = Camera.objects.create(
            organization=cls.org_b,
            created_by=cls.other_viewer,
            name="Tracking Summary Camera B",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.80.10",
        )

        cls.person_a = PersonProfile.objects.create(
            organization=cls.org_a,
            name="Tracking Summary Person A",
            category=PersonProfile.Category.EMPLOYEE,
        )

        cls.person_b = PersonProfile.objects.create(
            organization=cls.org_b,
            name="Tracking Summary Person B",
            category=PersonProfile.Category.VISITOR,
        )

        cls.vehicle_a = VehicleProfile.objects.create(
            organization=cls.org_a,
            name="Tracking Summary Vehicle A",
            category=VehicleProfile.Category.EMPLOYEE,
            vehicle_type=VehicleProfile.VehicleType.CAR,
            registration_number="UP70AA1111",
        )

        cls.session_a = TrackingSession.objects.create(
            organization=cls.org_a,
            camera=cls.camera_a,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id="tracking-summary-a",
            person_profile=cls.person_a,
            label="Tracking Summary Person A",
            status=TrackingSession.Status.ACTIVE,
            first_seen_at=now - timedelta(minutes=10),
            last_seen_at=now,
            first_seen_x=10.0,
            first_seen_y=20.0,
            last_seen_x=30.0,
            last_seen_y=40.0,
            total_distance=25.5,
            camera_count=1,
            zone_count=2,
            total_detections=15,
        )

        cls.session_b = TrackingSession.objects.create(
            organization=cls.org_b,
            camera=cls.camera_b,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id="tracking-summary-b",
            person_profile=cls.person_b,
            label="Tracking Summary Person B",
            status=TrackingSession.Status.ENDED,
            first_seen_at=now - timedelta(minutes=20),
            last_seen_at=now - timedelta(minutes=5),
            total_distance=40.0,
            camera_count=1,
            zone_count=1,
            total_detections=20,
        )

        cls.session_a_old = TrackingSession.objects.create(
            organization=cls.org_a,
            camera=cls.camera_a,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id="tracking-summary-multi",
            person_profile=cls.person_a,
            label="Older Session",
            status=TrackingSession.Status.ENDED,
            first_seen_at=now - timedelta(hours=2),
            last_seen_at=now - timedelta(hours=1),
            total_detections=5,
        )

        cls.session_a_latest = TrackingSession.objects.create(
            organization=cls.org_a,
            camera=cls.camera_a,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id="tracking-summary-multi",
            person_profile=cls.person_a,
            label="Latest Session",
            status=TrackingSession.Status.ACTIVE,
            first_seen_at=now - timedelta(minutes=15),
            last_seen_at=now,
            total_detections=25,
        )

        cls.point_summary = TrackingPoint.objects.create(
            tracking_session=cls.session_a,
            camera=cls.camera_a,
            occurred_at=now - timedelta(minutes=4),
            x=0.11,
            y=0.22,
            width=0.33,
            height=0.44,
            confidence=97.50,
            zone="Summary Entrance",
            metadata={"source": "summary-test"},
        )

        cls.location_summary = TrackingLocation.objects.create(
            tracking_session=cls.session_a,
            camera=cls.camera_a,
            zone="Summary Lobby",
            entered_at=now - timedelta(minutes=8),
            exited_at=now - timedelta(minutes=3),
            duration_seconds=300,
            first_x=0.12,
            first_y=0.23,
            last_x=0.34,
            last_y=0.45,
        )

        cls.visit_summary = TrackingCameraVisit.objects.create(
            tracking_session=cls.session_a,
            camera=cls.camera_a,
            entered_at=now - timedelta(minutes=9),
            exited_at=now - timedelta(minutes=2),
            duration_seconds=420,
            first_x=0.13,
            first_y=0.24,
            last_x=0.35,
            last_y=0.46,
            detection_count=14,
            metadata={"source": "summary-camera"},
        )

        cls.identity_summary = IdentityMatch.objects.create(
            organization=cls.org_a,
            tracking_session=cls.session_a,
            person_profile=cls.person_a,
            identity_type=IdentityMatch.IdentityType.PERSON,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=98.25,
            matched_at=now - timedelta(minutes=2),
            is_confirmed=True,
            metadata={"source": "summary-identity"},
        )

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_viewer_can_access_own_tracking_summary(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            "/api/tracking/tracking-summary-a/"
        )

        self.assertEqual(response.status_code, 200)

        self.assertIsInstance(response.data, dict)

    def test_viewer_cannot_access_other_organization_tracking_summary(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            "/api/tracking/tracking-summary-b/"
        )

        self.assertEqual(response.status_code, 404)

    def test_operator_can_access_own_tracking_summary(self):
        self.authenticate(self.operator)

        response = self.client.get(
            "/api/tracking/tracking-summary-a/"
        )

        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_own_tracking_summary(self):
        self.authenticate(self.admin)

        response = self.client.get(
            "/api/tracking/tracking-summary-a/"
        )

        self.assertEqual(response.status_code, 200)

    def test_other_organization_viewer_can_access_own_tracking_summary(self):
        self.authenticate(self.other_viewer)

        response = self.client.get(
            "/api/tracking/tracking-summary-b/"
        )

        self.assertEqual(response.status_code, 200)

    def test_other_organization_viewer_cannot_access_org_a_tracking_summary(
        self,
    ):
        self.authenticate(self.other_viewer)

        response = self.client.get(
            "/api/tracking/tracking-summary-a/"
        )

        self.assertEqual(response.status_code, 404)

    def test_missing_tracking_id_returns_404(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            "/api/tracking/does-not-exist/"
        )

        self.assertEqual(response.status_code, 404)

    def test_latest_session_is_selected_for_duplicate_tracking_id(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            "/api/tracking/tracking-summary-multi/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.data

        # The summary service should represent the latest session.
        self.assertIn(
            self.session_a_latest.tracking_id,
            str(data),
        )

        self.assertNotEqual(
            data,
            {},
        )

    def test_tracking_summary_returns_complete_session_payload(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            "/api/tracking/tracking-summary-a/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.data

        self.assertIn("session", data)
        self.assertIn("points", data)
        self.assertIn("locations", data)
        self.assertIn("camera_visits", data)
        self.assertIn("identities", data)

        session = data["session"]

        self.assertEqual(
            session["id"],
            self.session_a.id,
        )
        self.assertEqual(
            session["tracking_id"],
            "tracking-summary-a",
        )
        self.assertEqual(
            session["object_type"],
            TrackingSession.ObjectType.PERSON,
        )
        self.assertEqual(
            session["label"],
            "Tracking Summary Person A",
        )
        self.assertEqual(
            session["status"],
            TrackingSession.Status.ACTIVE,
        )
        self.assertEqual(
            session["total_detections"],
            15,
        )
        self.assertEqual(
            float(session["total_distance"]),
            25.5,
        )
        self.assertEqual(
            session["camera_count"],
            1,
        )
        self.assertEqual(
            session["zone_count"],
            2,
        )

        self.assertEqual(len(data["points"]), 1)
        self.assertEqual(
            data["points"][0]["id"],
            self.point_summary.id,
        )
        self.assertEqual(
            data["points"][0]["camera_id"],
            self.camera_a.id,
        )
        self.assertEqual(
            data["points"][0]["camera"],
            self.camera_a.name,
        )
        self.assertEqual(
            data["points"][0]["zone"],
            "Summary Entrance",
        )
        self.assertEqual(
            float(data["points"][0]["confidence"]),
            97.50,
        )

        self.assertEqual(len(data["locations"]), 1)
        self.assertEqual(
            data["locations"][0]["id"],
            self.location_summary.id,
        )
        self.assertEqual(
            data["locations"][0]["camera_id"],
            self.camera_a.id,
        )
        self.assertEqual(
            data["locations"][0]["camera"],
            self.camera_a.name,
        )
        self.assertEqual(
            data["locations"][0]["zone"],
            "Summary Lobby",
        )
        self.assertEqual(
            data["locations"][0]["duration_seconds"],
            300,
        )

        self.assertEqual(len(data["camera_visits"]), 1)
        self.assertEqual(
            data["camera_visits"][0]["id"],
            self.visit_summary.id,
        )
        self.assertEqual(
            data["camera_visits"][0]["camera_id"],
            self.camera_a.id,
        )
        self.assertEqual(
            data["camera_visits"][0]["camera"],
            self.camera_a.name,
        )
        self.assertEqual(
            data["camera_visits"][0]["detection_count"],
            14,
        )

        self.assertEqual(len(data["identities"]), 1)
        self.assertEqual(
            data["identities"][0]["id"],
            self.identity_summary.id,
        )
        self.assertEqual(
            data["identities"][0]["identity_type"],
            IdentityMatch.IdentityType.PERSON,
        )
        self.assertEqual(
            data["identities"][0]["match_method"],
            IdentityMatch.MatchMethod.FACE,
        )
        self.assertEqual(
            float(data["identities"][0]["confidence"]),
            98.25,
        )
        self.assertTrue(
            data["identities"][0]["is_confirmed"]
        )
        self.assertEqual(
            data["identities"][0]["person"],
            self.person_a.name,
        )
        self.assertIsNone(
            data["identities"][0]["vehicle"]
        )

    def test_tracking_summary_does_not_leak_other_session_data(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            "/api/tracking/tracking-summary-a/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.data

        point_ids = {
            item["id"]
            for item in data["points"]
        }
        location_ids = {
            item["id"]
            for item in data["locations"]
        }
        visit_ids = {
            item["id"]
            for item in data["camera_visits"]
        }

        self.assertIn(
            self.point_summary.id,
            point_ids,
        )
        self.assertIn(
            self.location_summary.id,
            location_ids,
        )
        self.assertIn(
            self.visit_summary.id,
            visit_ids,
        )

        self.assertNotIn(
            self.session_b.id,
            point_ids,
        )
        self.assertNotIn(
            self.session_b.id,
            location_ids,
        )
        self.assertNotIn(
            self.session_b.id,
            visit_ids,
        )

    def test_tracking_summary_child_data_is_scoped_to_selected_session(self):
        extra_point = TrackingPoint.objects.create(
            tracking_session=self.session_a_latest,
            camera=self.camera_a,
            occurred_at=timezone.now(),
            x=0.90,
            y=0.90,
            width=0.10,
            height=0.10,
            confidence=80.00,
            zone="Latest Session Zone",
        )

        self.authenticate(self.viewer)

        response = self.client.get(
            "/api/tracking/tracking-summary-multi/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.data

        point_ids = {
            item["id"]
            for item in data["points"]
        }

        self.assertIn(
            extra_point.id,
            point_ids,
        )

        self.assertNotIn(
            self.point_summary.id,
            point_ids,
        )

    def test_tracking_summary_requires_authentication(self):
        response = self.client.get(
            "/api/tracking/tracking-summary-a/"
        )

        self.assertEqual(response.status_code, 401)


class TrackingDetailAPIAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()

        cls.org_a = Organization.objects.create(
            name="Tracking Detail API Organization A",
            slug="tracking-detail-api-org-a",
        )

        cls.org_b = Organization.objects.create(
            name="Tracking Detail API Organization B",
            slug="tracking-detail-api-org-b",
        )

        cls.viewer_group = Group.objects.create(
            name=ROLE_VIEWER
        )

        cls.super_admin_group = Group.objects.create(
            name=ROLE_SUPER_ADMIN
        )

        cls.viewer_a = User.objects.create_user(
            username="tracking_detail_viewer_a",
            password="TrackingDetailPass123!",
            is_active=True,
        )
        cls.viewer_a.organization = cls.org_a
        cls.viewer_a.save(update_fields=["organization"])
        cls.viewer_a.groups.add(cls.viewer_group)

        cls.viewer_b = User.objects.create_user(
            username="tracking_detail_viewer_b",
            password="TrackingDetailPass123!",
            is_active=True,
        )
        cls.viewer_b.organization = cls.org_b
        cls.viewer_b.save(update_fields=["organization"])
        cls.viewer_b.groups.add(cls.viewer_group)

        cls.super_admin = User.objects.create_user(
            username="tracking_detail_super_admin",
            password="TrackingDetailPass123!",
            is_active=True,
        )
        cls.super_admin.groups.add(cls.super_admin_group)

        cls.camera_a = Camera.objects.create(
            organization=cls.org_a,
            created_by=cls.viewer_a,
            name="Tracking Detail Camera A",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.90.10",
        )

        cls.camera_b = Camera.objects.create(
            organization=cls.org_b,
            created_by=cls.viewer_b,
            name="Tracking Detail Camera B",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.91.10",
        )

        cls.person_a = PersonProfile.objects.create(
            organization=cls.org_a,
            name="Tracking Detail Person A",
            category=PersonProfile.Category.EMPLOYEE,
        )

        cls.person_b = PersonProfile.objects.create(
            organization=cls.org_b,
            name="Tracking Detail Person B",
            category=PersonProfile.Category.VISITOR,
        )

        cls.session_a = TrackingSession.objects.create(
            organization=cls.org_a,
            camera=cls.camera_a,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id="detail-track-a",
            person_profile=cls.person_a,
            label="Tracking Detail Person A",
            status=TrackingSession.Status.ACTIVE,
            first_seen_at=now - timedelta(minutes=15),
            last_seen_at=now,
            total_detections=10,
        )

        cls.session_b = TrackingSession.objects.create(
            organization=cls.org_b,
            camera=cls.camera_b,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id="detail-track-b",
            person_profile=cls.person_b,
            label="Tracking Detail Person B",
            status=TrackingSession.Status.ENDED,
            first_seen_at=now - timedelta(minutes=20),
            last_seen_at=now - timedelta(minutes=5),
            total_detections=12,
        )

        cls.detection_a = Detection.objects.create(
            organization=cls.org_a,
            camera=cls.camera_a,
            object_type=Detection.ObjectType.PERSON,
            label="Person A Detection",
            confidence=96.50,
            tracking_id="detail-track-a",
            status=Detection.DetectionStatus.ACTIVE,
            first_seen_at=now - timedelta(minutes=5),
            last_seen_at=now,
            bbox_x=0.10,
            bbox_y=0.20,
            bbox_width=0.30,
            bbox_height=0.40,
            metadata={"source": "test-a"},
        )

        cls.detection_b = Detection.objects.create(
            organization=cls.org_b,
            camera=cls.camera_b,
            object_type=Detection.ObjectType.PERSON,
            label="Person B Detection",
            confidence=91.25,
            tracking_id="detail-track-b",
            status=Detection.DetectionStatus.ENDED,
            first_seen_at=now - timedelta(minutes=10),
            last_seen_at=now - timedelta(minutes=5),
            bbox_x=0.15,
            bbox_y=0.25,
            bbox_width=0.35,
            bbox_height=0.45,
            metadata={"source": "test-b"},
        )

        cls.point_a = TrackingPoint.objects.create(
            tracking_session=cls.session_a,
            camera=cls.camera_a,
            occurred_at=now - timedelta(minutes=3),
            x=0.25,
            y=0.35,
            width=0.20,
            height=0.30,
            confidence=95.00,
            zone="Entrance",
            metadata={"source": "camera-a"},
        )

        cls.point_b = TrackingPoint.objects.create(
            tracking_session=cls.session_b,
            camera=cls.camera_b,
            occurred_at=now - timedelta(minutes=7),
            x=0.45,
            y=0.55,
            width=0.25,
            height=0.35,
            confidence=88.00,
            zone="Parking",
            metadata={"source": "camera-b"},
        )

        cls.location_a = TrackingLocation.objects.create(
            tracking_session=cls.session_a,
            camera=cls.camera_a,
            zone="Lobby",
            entered_at=now - timedelta(minutes=8),
            exited_at=now - timedelta(minutes=2),
            duration_seconds=360,
            first_x=0.10,
            first_y=0.20,
            last_x=0.40,
            last_y=0.50,
        )

        cls.location_b = TrackingLocation.objects.create(
            tracking_session=cls.session_b,
            camera=cls.camera_b,
            zone="Parking",
            entered_at=now - timedelta(minutes=12),
            exited_at=now - timedelta(minutes=6),
            duration_seconds=360,
            first_x=0.20,
            first_y=0.30,
            last_x=0.50,
            last_y=0.60,
        )

        cls.visit_a = TrackingCameraVisit.objects.create(
            tracking_session=cls.session_a,
            camera=cls.camera_a,
            entered_at=now - timedelta(minutes=10),
            exited_at=now - timedelta(minutes=4),
            duration_seconds=360,
            first_x=0.15,
            first_y=0.25,
            last_x=0.45,
            last_y=0.55,
            detection_count=8,
            metadata={"camera": "A"},
        )

        cls.visit_b = TrackingCameraVisit.objects.create(
            tracking_session=cls.session_b,
            camera=cls.camera_b,
            entered_at=now - timedelta(minutes=15),
            exited_at=now - timedelta(minutes=8),
            duration_seconds=420,
            first_x=0.25,
            first_y=0.35,
            last_x=0.55,
            last_y=0.65,
            detection_count=9,
            metadata={"camera": "B"},
        )

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_viewer_can_list_own_detections(self):
        self.authenticate(self.viewer_a)

        response = self.client.get("/api/detections/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            self.detection_a.id,
        )

    def test_viewer_cannot_retrieve_other_organization_detection(self):
        self.authenticate(self.viewer_a)

        response = self.client.get(
            f"/api/detections/{self.detection_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_viewer_can_retrieve_own_detection(self):
        self.authenticate(self.viewer_a)

        response = self.client.get(
            f"/api/detections/{self.detection_a.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.detection_a.id)

    def test_viewer_can_list_own_tracking_points(self):
        self.authenticate(self.viewer_a)

        response = self.client.get("/api/tracking-points/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            self.point_a.id,
        )

    def test_viewer_cannot_retrieve_other_organization_tracking_point(self):
        self.authenticate(self.viewer_a)

        response = self.client.get(
            f"/api/tracking-points/{self.point_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_viewer_can_list_own_tracking_locations(self):
        self.authenticate(self.viewer_a)

        response = self.client.get("/api/tracking-locations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            self.location_a.id,
        )

    def test_viewer_cannot_retrieve_other_organization_tracking_location(
        self,
    ):
        self.authenticate(self.viewer_a)

        response = self.client.get(
            f"/api/tracking-locations/{self.location_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_viewer_can_list_own_tracking_camera_visits(self):
        self.authenticate(self.viewer_a)

        response = self.client.get(
            "/api/tracking-camera-visits/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            self.visit_a.id,
        )

    def test_viewer_cannot_retrieve_other_organization_camera_visit(
        self,
    ):
        self.authenticate(self.viewer_a)

        response = self.client.get(
            f"/api/tracking-camera-visits/{self.visit_b.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_other_organization_viewer_sees_only_own_tracking_data(self):
        self.authenticate(self.viewer_b)

        point_response = self.client.get(
            "/api/tracking-points/"
        )
        location_response = self.client.get(
            "/api/tracking-locations/"
        )
        visit_response = self.client.get(
            "/api/tracking-camera-visits/"
        )

        self.assertEqual(point_response.status_code, 200)
        self.assertEqual(location_response.status_code, 200)
        self.assertEqual(visit_response.status_code, 200)

        self.assertEqual(
            len(point_response.data),
            1,
        )
        self.assertEqual(
            len(location_response.data),
            1,
        )
        self.assertEqual(
            len(visit_response.data),
            1,
        )

        self.assertEqual(
            point_response.data[0]["id"],
            self.point_b.id,
        )
        self.assertEqual(
            location_response.data[0]["id"],
            self.location_b.id,
        )
        self.assertEqual(
            visit_response.data[0]["id"],
            self.visit_b.id,
        )

    def test_super_admin_can_retrieve_cross_organization_detection(
        self,
    ):
        self.authenticate(self.super_admin)

        response = self.client.get(
            f"/api/detections/{self.detection_b.id}/"
        )

        self.assertEqual(response.status_code, 200)

    def test_super_admin_can_retrieve_cross_organization_tracking_point(
        self,
    ):
        self.authenticate(self.super_admin)

        response = self.client.get(
            f"/api/tracking-points/{self.point_b.id}/"
        )

        self.assertEqual(response.status_code, 200)

    def test_super_admin_can_retrieve_cross_organization_tracking_location(
        self,
    ):
        self.authenticate(self.super_admin)

        response = self.client.get(
            f"/api/tracking-locations/{self.location_b.id}/"
        )

        self.assertEqual(response.status_code, 200)

    def test_super_admin_can_retrieve_cross_organization_camera_visit(
        self,
    ):
        self.authenticate(self.super_admin)

        response = self.client.get(
            f"/api/tracking-camera-visits/{self.visit_b.id}/"
        )

        self.assertEqual(response.status_code, 200)

    def test_tracking_detail_endpoints_require_authentication(self):
        endpoints = [
            "/api/detections/",
            "/api/tracking-points/",
            "/api/tracking-locations/",
            "/api/tracking-camera-visits/",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 401)



