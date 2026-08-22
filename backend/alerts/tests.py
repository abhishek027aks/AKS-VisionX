from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Organization
from alerts.models import Alert
from cameras.models import Camera
from events.models import Event

from api.permissions import ROLE_OPERATOR

from api.permissions import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
)


User = get_user_model()


class AlertAPIAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()

        cls.org_a = Organization.objects.create(
            name="Alert API Isolation Organization A",
            slug="alert-api-isolation-org-a",
        )

        cls.org_b = Organization.objects.create(
            name="Alert API Isolation Organization B",
            slug="alert-api-isolation-org-b",
        )

        cls.viewer_group = Group.objects.create(
            name=ROLE_VIEWER,
        )

        cls.operator_group = Group.objects.create(
            name=ROLE_OPERATOR,
        )

        cls.admin_group = Group.objects.create(
            name=ROLE_ADMIN,
        )

        cls.viewer = User.objects.create_user(
            username="alert_viewer",
            password="AlertTestPass123!",
            is_active=True,
        )
        cls.viewer.organization = cls.org_a
        cls.viewer.save(
            update_fields=["organization"],
        )
        cls.viewer.groups.add(cls.viewer_group)

        cls.operator = User.objects.create_user(
            username="alert_operator",
            password="AlertTestPass123!",
            is_active=True,
        )
        cls.operator.organization = cls.org_a
        cls.operator.save(
            update_fields=["organization"],
        )
        cls.operator.groups.add(cls.operator_group)

        cls.admin = User.objects.create_user(
            username="alert_admin",
            password="AlertTestPass123!",
            is_active=True,
        )
        cls.admin.organization = cls.org_a
        cls.admin.save(
            update_fields=["organization"],
        )
        cls.admin.groups.add(cls.admin_group)

        cls.other_viewer = User.objects.create_user(
            username="alert_other_viewer",
            password="AlertTestPass123!",
            is_active=True,
        )
        cls.other_viewer.organization = cls.org_b
        cls.other_viewer.save(
            update_fields=["organization"],
        )
        cls.other_viewer.groups.add(cls.viewer_group)

        cls.camera_a = Camera.objects.create(
            organization=cls.org_a,
            created_by=cls.operator,
            name="Alert Camera A",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.70.10",
        )

        cls.camera_b = Camera.objects.create(
            organization=cls.org_b,
            created_by=cls.other_viewer,
            name="Alert Camera B",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.80.10",
        )

        cls.event_a = Event.objects.create(
            organization=cls.org_a,
            camera=cls.camera_a,
            event_type=Event.EventType.PERSON,
            status=Event.Status.NEW,
            title="Person Event A",
            description="Organization A event",
            occurred_at=now,
            confidence="95.00",
        )

        cls.event_b = Event.objects.create(
            organization=cls.org_b,
            camera=cls.camera_b,
            event_type=Event.EventType.VEHICLE,
            status=Event.Status.NEW,
            title="Vehicle Event B",
            description="Organization B event",
            occurred_at=now,
            confidence="91.00",
        )

        cls.alert_a = Alert.objects.create(
            organization=cls.org_a,
            camera=cls.camera_a,
            event=cls.event_a,
            source=Alert.Source.EVENT,
            severity=Alert.Severity.HIGH,
            status=Alert.Status.NEW,
            title="Person Alert A",
            message="Organization A alert",
        )

        cls.alert_b = Alert.objects.create(
            organization=cls.org_b,
            camera=cls.camera_b,
            event=cls.event_b,
            source=Alert.Source.EVENT,
            severity=Alert.Severity.MEDIUM,
            status=Alert.Status.NEW,
            title="Vehicle Alert B",
            message="Organization B alert",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def alert_payload(
        self,
        camera_id,
        event_id=None,
        title="Test Alert",
    ):
        payload = {
            "camera": camera_id,
            "source": "EVENT",
            "severity": "HIGH",
            "status": "NEW",
            "title": title,
            "message": "API authorization test alert",
        }

        if event_id is not None:
            payload["event"] = event_id

        return payload

    def test_viewer_can_list_own_organization_alerts(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            "/api/alerts/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = {
            item["id"]
            for item in response.data
        }

        self.assertIn(
            self.alert_a.id,
            ids,
        )

        self.assertNotIn(
            self.alert_b.id,
            ids,
        )

    def test_viewer_can_retrieve_own_organization_alert(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/alerts/{self.alert_a.id}/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            self.alert_a.id,
        )

    def test_viewer_cannot_retrieve_other_organization_alert(self):
        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/alerts/{self.alert_b.id}/",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_viewer_cannot_create_alert(self):
        self.authenticate(self.viewer)

        response = self.client.post(
            "/api/alerts/",
            self.alert_payload(
                self.camera_a.id,
                self.event_a.id,
                "Viewer Alert",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_operator_can_create_alert(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/alerts/",
            self.alert_payload(
                self.camera_a.id,
                self.event_a.id,
                "Operator Alert",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["organization"],
            self.org_a.id,
        )

        self.assertEqual(
            response.data["camera"],
            self.camera_a.id,
        )

        self.assertEqual(
            response.data["event"],
            self.event_a.id,
        )

        self.assertTrue(
            Alert.objects.filter(
                pk=response.data["id"],
                organization=self.org_a,
            ).exists()
        )

    def test_operator_cannot_create_alert_for_other_organization_camera(
        self,
    ):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/alerts/",
            self.alert_payload(
                self.camera_b.id,
                None,
                "Cross Organization Camera Alert",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            Alert.objects.filter(
                title="Cross Organization Camera Alert",
            ).exists()
        )

    def test_operator_cannot_create_alert_for_other_organization_event(
        self,
    ):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/alerts/",
            self.alert_payload(
                self.camera_a.id,
                self.event_b.id,
                "Cross Organization Event Alert",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            Alert.objects.filter(
                title="Cross Organization Event Alert",
            ).exists()
        )

    def test_operator_can_update_own_organization_alert(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/alerts/{self.alert_a.id}/",
            {
                "title": "Updated Alert A",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.alert_a.refresh_from_db()

        self.assertEqual(
            self.alert_a.title,
            "Updated Alert A",
        )

    def test_operator_cannot_update_other_organization_alert(self):
        self.authenticate(self.operator)

        response = self.client.patch(
            f"/api/alerts/{self.alert_b.id}/",
            {
                "title": "Hacked Alert",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.alert_b.refresh_from_db()

        self.assertEqual(
            self.alert_b.title,
            "Vehicle Alert B",
        )

    def test_operator_cannot_delete_alert(self):
        self.authenticate(self.operator)

        response = self.client.delete(
            f"/api/alerts/{self.alert_a.id}/",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertTrue(
            Alert.objects.filter(
                pk=self.alert_a.id,
            ).exists()
        )

    def test_admin_can_delete_own_organization_alert(self):
        self.authenticate(self.admin)

        alert = Alert.objects.create(
            organization=self.org_a,
            camera=self.camera_a,
            event=self.event_a,
            source=Alert.Source.EVENT,
            severity=Alert.Severity.MEDIUM,
            status=Alert.Status.NEW,
            title="Admin Delete Alert",
            message="Delete test",
        )

        response = self.client.delete(
            f"/api/alerts/{alert.id}/",
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            Alert.objects.filter(
                pk=alert.id,
            ).exists()
        )

    def test_admin_cannot_delete_other_organization_alert(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            f"/api/alerts/{self.alert_b.id}/",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTrue(
            Alert.objects.filter(
                pk=self.alert_b.id,
            ).exists()
        )


class AlertStatusLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Alert Lifecycle Organization",
            slug="alert-lifecycle-organization",
        )

        cls.operator_group = Group.objects.create(
            name=ROLE_OPERATOR,
        )

        cls.operator = User.objects.create_user(
            username="alert_lifecycle_operator",
            password="AlertTestPass123!",
            is_active=True,
        )

        cls.operator.organization = cls.organization
        cls.operator.save(
            update_fields=["organization"],
        )

        cls.operator.groups.add(
            cls.operator_group,
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            created_by=cls.operator,
            name="Lifecycle Alert Camera",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.90.10",
        )

        cls.event = Event.objects.create(
            organization=cls.organization,
            camera=cls.camera,
            event_type=Event.EventType.PERSON,
            status=Event.Status.NEW,
            title="Lifecycle Event",
            occurred_at=timezone.now(),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"
        self.client.force_authenticate(
            user=self.operator,
        )

    def create_alert(self, title):
        return Alert.objects.create(
            organization=self.organization,
            camera=self.camera,
            event=self.event,
            source=Alert.Source.EVENT,
            severity=Alert.Severity.HIGH,
            status=Alert.Status.NEW,
            title=title,
            message="Lifecycle test alert",
        )

    def test_new_to_acknowledged_is_allowed(self):
        alert = self.create_alert(
            "NEW TO ACKNOWLEDGED",
        )

        response = self.client.patch(
            f"/api/alerts/{alert.id}/",
            {
                "status": "ACKNOWLEDGED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        alert.refresh_from_db()

        self.assertEqual(
            alert.status,
            Alert.Status.ACKNOWLEDGED,
        )

        self.assertIsNotNone(
            alert.acknowledged_at,
        )

    def test_new_to_resolved_is_rejected(self):
        alert = self.create_alert(
            "NEW TO RESOLVED",
        )

        response = self.client.patch(
            f"/api/alerts/{alert.id}/",
            {
                "status": "RESOLVED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "status",
            response.data,
        )

        alert.refresh_from_db()

        self.assertEqual(
            alert.status,
            Alert.Status.NEW,
        )

        self.assertIsNone(
            alert.resolved_at,
        )

    def test_acknowledged_to_resolved_is_allowed(self):
        alert = self.create_alert(
            "ACKNOWLEDGED TO RESOLVED",
        )

        alert.status = Alert.Status.ACKNOWLEDGED
        alert.save(
            update_fields=["status"],
        )

        response = self.client.patch(
            f"/api/alerts/{alert.id}/",
            {
                "status": "RESOLVED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        alert.refresh_from_db()

        self.assertEqual(
            alert.status,
            Alert.Status.RESOLVED,
        )

        self.assertIsNotNone(
            alert.resolved_at,
        )

        self.assertIsNotNone(
            alert.acknowledged_at,
        )

    def test_new_to_dismissed_is_allowed(self):
        alert = self.create_alert(
            "NEW TO DISMISSED",
        )

        response = self.client.patch(
            f"/api/alerts/{alert.id}/",
            {
                "status": "DISMISSED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        alert.refresh_from_db()

        self.assertEqual(
            alert.status,
            Alert.Status.DISMISSED,
        )

    def test_dismissed_to_resolved_is_rejected(self):
        alert = self.create_alert(
            "DISMISSED TO RESOLVED",
        )

        alert.status = Alert.Status.DISMISSED
        alert.save(
            update_fields=["status"],
        )

        response = self.client.patch(
            f"/api/alerts/{alert.id}/",
            {
                "status": "RESOLVED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        alert.refresh_from_db()

        self.assertEqual(
            alert.status,
            Alert.Status.DISMISSED,
        )

    def test_resolved_to_acknowledged_is_rejected(self):
        alert = self.create_alert(
            "RESOLVED TO ACKNOWLEDGED",
        )

        alert.status = Alert.Status.RESOLVED
        alert.save(
            update_fields=["status"],
        )

        response = self.client.patch(
            f"/api/alerts/{alert.id}/",
            {
                "status": "ACKNOWLEDGED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        alert.refresh_from_db()

        self.assertEqual(
            alert.status,
            Alert.Status.RESOLVED,
        )

    def test_new_alert_must_start_with_new_status(self):
        payload = {
            "camera": self.camera.id,
            "event": self.event.id,
            "source": "EVENT",
            "severity": "HIGH",
            "status": "RESOLVED",
            "title": "Invalid Initial Alert",
            "message": "Invalid initial status",
        }

        response = self.client.post(
            "/api/alerts/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "status",
            response.data,
        )

    def test_acknowledged_timestamp_is_not_cleared_by_non_status_update(
        self,
    ):
        alert = self.create_alert(
            "Timestamp Preservation",
        )

        alert.status = Alert.Status.ACKNOWLEDGED
        alert.save(
            update_fields=["status"],
        )

        response = self.client.patch(
            f"/api/alerts/{alert.id}/",
            {
                "title": "Changed Title",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        alert.refresh_from_db()

        self.assertEqual(
            alert.title,
            "Changed Title",
        )

        self.assertIsNotNone(
            alert.acknowledged_at,
        )
