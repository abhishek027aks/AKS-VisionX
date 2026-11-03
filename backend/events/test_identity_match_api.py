from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from accounts.models import Organization
from cameras.models import Camera
from events.models import (
    IdentityMatch,
    PersonProfile,
    VehicleProfile,
    TrackingSession,
)


User = get_user_model()


class IdentityMatchAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            name="Phase 5 Identity Organization",
            slug="phase-5-identity-organization",
        )

        cls.other_organization = Organization.objects.create(
            name="Phase 5 Identity Other Organization",
            slug="phase-5-identity-other-organization",
        )

        cls.viewer_group, _ = Group.objects.get_or_create(
            name="Viewer"
        )

        cls.operator_group, _ = Group.objects.get_or_create(
            name="Operator"
        )

        cls.super_admin_group, _ = Group.objects.get_or_create(
            name="Super Admin"
        )

        cls.user = User.objects.create_user(
            username="phase5identityuser",
            password="TestPassword123!",
            organization=cls.organization,
        )
        cls.user.groups.add(cls.operator_group)

        cls.viewer_user = User.objects.create_user(
            username="phase5identityviewer",
            password="TestPassword123!",
            organization=cls.organization,
        )
        cls.viewer_user.groups.add(cls.viewer_group)

        cls.other_user = User.objects.create_user(
            username="phase5identityotheruser",
            password="TestPassword123!",
            organization=cls.other_organization,
        )
        cls.other_user.groups.add(cls.operator_group)

        cls.super_admin = User.objects.create_user(
            username="phase5identitysuperadmin",
            password="TestPassword123!",
            organization=None,
        )
        cls.super_admin.groups.add(cls.super_admin_group)

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="Phase 5 Identity Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

        cls.other_camera = Camera.objects.create(
            organization=cls.other_organization,
            name="Phase 5 Other Identity Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

        cls.person = PersonProfile.objects.create(
            organization=cls.organization,
            name="Phase 5 Person",
            category=PersonProfile.Category.EMPLOYEE,
        )

        cls.other_person = PersonProfile.objects.create(
            organization=cls.other_organization,
            name="Other Organization Person",
            category=PersonProfile.Category.EMPLOYEE,
        )

        cls.vehicle = VehicleProfile.objects.create(
            organization=cls.organization,
            name="Phase 5 Vehicle",
            category=VehicleProfile.Category.PERSONAL,
            vehicle_type=VehicleProfile.VehicleType.CAR,
            registration_number="PHASE5-001",
        )

        cls.other_vehicle = VehicleProfile.objects.create(
            organization=cls.other_organization,
            name="Other Organization Vehicle",
            category=VehicleProfile.Category.PERSONAL,
            vehicle_type=VehicleProfile.VehicleType.CAR,
            registration_number="OTHER-001",
        )

    def setUp(self):
        self.client = APIClient()

    def authenticate(self, user=None):
        self.client.force_authenticate(
            user=user or self.user
        )

    def create_session(
        self,
        tracking_id="identity-api-test-1",
        organization=None,
        camera=None,
    ):
        organization = organization or self.organization
        camera = camera or self.camera

        occurred_at = timezone.now()

        return TrackingSession.objects.create(
            organization=organization,
            camera=camera,
            object_type=TrackingSession.ObjectType.PERSON,
            tracking_id=tracking_id,
            status=TrackingSession.Status.ACTIVE,
            first_seen_at=occurred_at,
            last_seen_at=occurred_at,
            label="unknown",
            total_detections=1,
            total_distance=Decimal("0"),
            camera_count=1,
            zone_count=1,
        )

    # ---------------------------------------------------------
    # Authentication / permissions
    # ---------------------------------------------------------

    def test_identity_list_requires_authentication(self):
        response = self.client.get(
            reverse("identity-match-list")
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )

    def test_viewer_can_list_identity_matches(self):
        session = self.create_session(
            tracking_id="viewer-list-1"
        )

        IdentityMatch.objects.create(
            organization=self.organization,
            tracking_session=session,
            person_profile=self.person,
            identity_type=IdentityMatch.IdentityType.PERSON,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=Decimal("0.95"),
            matched_at=timezone.now(),
            is_confirmed=True,
        )

        self.authenticate(self.viewer_user)

        response = self.client.get(
            reverse("identity-match-list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_viewer_cannot_create_identity_match(self):
        session = self.create_session(
            tracking_id="viewer-create-1"
        )

        self.authenticate(self.viewer_user)

        response = self.client.post(
            reverse("identity-match-list"),
            {
                "tracking_session": session.id,
                "person_profile": self.person.id,
                "identity_type": "PERSON",
                "match_method": "MANUAL",
                "confidence": "0.90",
                "is_confirmed": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # ---------------------------------------------------------
    # Person identity creation
    # ---------------------------------------------------------

    def test_operator_can_create_person_identity_match(self):
        session = self.create_session(
            tracking_id="person-create-1"
        )

        self.authenticate()

        response = self.client.post(
            reverse("identity-match-list"),
            {
                "tracking_session": session.id,
                "person_profile": self.person.id,
                "identity_type": "PERSON",
                "match_method": "FACE",
                "confidence": "0.96",
                "is_confirmed": True,
                "metadata": {
                    "source": "phase-5-test"
                },
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["identity_type"],
            "PERSON",
        )

        self.assertEqual(response.data["person"]["name"], "Phase 5 Person")

        self.assertIsNone(
            response.data["vehicle"],
        )

        self.assertEqual(
            str(response.data["confidence"]),
            "0.96",
        )

        self.assertEqual(
            response.data["metadata"]["source"],
            "phase-5-test",
        )

        created = IdentityMatch.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            created.organization_id,
            self.organization.id,
        )

    # ---------------------------------------------------------
    # Vehicle identity creation
    # ---------------------------------------------------------

    def test_operator_can_create_vehicle_identity_match(self):
        session = self.create_session(
            tracking_id="vehicle-create-1"
        )

        self.authenticate()

        response = self.client.post(
            reverse("identity-match-list"),
            {
                "tracking_session": session.id,
                "vehicle_profile": self.vehicle.id,
                "identity_type": "VEHICLE",
                "match_method": "PLATE",
                "confidence": "0.91",
                "is_confirmed": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["identity_type"],
            "VEHICLE",
        )

        self.assertEqual(response.data["vehicle"]["name"], "Phase 5 Vehicle")

        self.assertIsNone(
            response.data["person"],
        )

    # ---------------------------------------------------------
    # Organization isolation
    # ---------------------------------------------------------

    def test_other_organization_session_cannot_be_used(self):
        session = self.create_session(
            tracking_id="other-session-1",
            organization=self.other_organization,
            camera=self.other_camera,
        )

        self.authenticate()

        response = self.client.post(
            reverse("identity-match-list"),
            {
                "tracking_session": session.id,
                "person_profile": self.person.id,
                "identity_type": "PERSON",
                "match_method": "MANUAL",
                "confidence": "0.90",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "tracking_session",
            response.data,
        )

    def test_other_organization_person_cannot_be_linked(self):
        session = self.create_session(
            tracking_id="other-person-1"
        )

        self.authenticate()

        response = self.client.post(
            reverse("identity-match-list"),
            {
                "tracking_session": session.id,
                "person_profile": self.other_person.id,
                "identity_type": "PERSON",
                "match_method": "FACE",
                "confidence": "0.88",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "person_profile",
            response.data,
        )

    def test_other_organization_vehicle_cannot_be_linked(self):
        session = self.create_session(
            tracking_id="other-vehicle-1"
        )

        self.authenticate()

        response = self.client.post(
            reverse("identity-match-list"),
            {
                "tracking_session": session.id,
                "vehicle_profile": self.other_vehicle.id,
                "identity_type": "VEHICLE",
                "match_method": "PLATE",
                "confidence": "0.88",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "vehicle_profile",
            response.data,
        )

    def test_identity_list_hides_other_organization(self):
        session = self.create_session(
            tracking_id="private-identity-1",
            organization=self.other_organization,
            camera=self.other_camera,
        )

        IdentityMatch.objects.create(
            organization=self.other_organization,
            tracking_session=session,
            person_profile=self.other_person,
            identity_type=IdentityMatch.IdentityType.PERSON,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=Decimal("0.90"),
            matched_at=timezone.now(),
        )

        self.authenticate()

        response = self.client.get(
            reverse("identity-match-list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            0,
        )

    # ---------------------------------------------------------
    # Identity type consistency
    # ---------------------------------------------------------

    def test_person_identity_rejects_vehicle_only_link(self):
        session = self.create_session(
            tracking_id="person-type-vehicle-1"
        )

        self.authenticate()

        response = self.client.post(
            reverse("identity-match-list"),
            {
                "tracking_session": session.id,
                "vehicle_profile": self.vehicle.id,
                "identity_type": "PERSON",
                "match_method": "FACE",
                "confidence": "0.90",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_vehicle_identity_rejects_person_only_link(self):
        session = self.create_session(
            tracking_id="vehicle-type-person-1"
        )

        self.authenticate()

        response = self.client.post(
            reverse("identity-match-list"),
            {
                "tracking_session": session.id,
                "person_profile": self.person.id,
                "identity_type": "VEHICLE",
                "match_method": "PLATE",
                "confidence": "0.90",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    # ---------------------------------------------------------
    # Super Admin
    # ---------------------------------------------------------

    def test_super_admin_can_create_cross_organization_identity(self):
        session = self.create_session(
            tracking_id="super-admin-cross-org-1",
            organization=self.other_organization,
            camera=self.other_camera,
        )

        self.authenticate(self.super_admin)

        response = self.client.post(
            reverse("identity-match-list"),
            {
                "tracking_session": session.id,
                "person_profile": self.other_person.id,
                "identity_type": "PERSON",
                "match_method": "MANUAL",
                "confidence": "0.99",
                "is_confirmed": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["organization"],
            self.other_organization.id,
        )

    def test_super_admin_can_list_all_organizations(self):
        session_a = self.create_session(
            tracking_id="super-list-a"
        )

        session_b = self.create_session(
            tracking_id="super-list-b",
            organization=self.other_organization,
            camera=self.other_camera,
        )

        IdentityMatch.objects.create(
            organization=self.organization,
            tracking_session=session_a,
            person_profile=self.person,
            identity_type=IdentityMatch.IdentityType.PERSON,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=Decimal("0.95"),
            matched_at=timezone.now(),
        )

        IdentityMatch.objects.create(
            organization=self.other_organization,
            tracking_session=session_b,
            person_profile=self.other_person,
            identity_type=IdentityMatch.IdentityType.PERSON,
            match_method=IdentityMatch.MatchMethod.FACE,
            confidence=Decimal("0.94"),
            matched_at=timezone.now(),
        )

        self.authenticate(self.super_admin)

        response = self.client.get(
            reverse("identity-match-list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            2,
        )

    # ---------------------------------------------------------
    # Required tracking session
    # ---------------------------------------------------------

    def test_tracking_session_is_required(self):
        self.authenticate()

        response = self.client.post(
            reverse("identity-match-list"),
            {
                "person_profile": self.person.id,
                "identity_type": "PERSON",
                "match_method": "FACE",
                "confidence": "0.90",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "tracking_session",
            response.data,
        )


