from rest_framework.permissions import BasePermission


ROLE_SUPER_ADMIN = "Super Admin"
ROLE_ADMIN = "Admin"
ROLE_OPERATOR = "Operator"
ROLE_VIEWER = "Viewer"


def has_role(user, role):
    if not user or not user.is_authenticated:
        return False

    return user.groups.filter(name=role).exists()


def has_any_role(user, roles):
    if not user or not user.is_authenticated:
        return False

    return user.groups.filter(name__in=roles).exists()


def is_super_admin(user):
    return has_role(user, ROLE_SUPER_ADMIN)


def get_user_organization(user):
    if not user or not user.is_authenticated:
        return None

    return user.organization


class IsSuperAdmin(BasePermission):
    message = "Super Admin permission required."

    def has_permission(self, request, view):
        return is_super_admin(request.user)


class IsAdminOrSuperAdmin(BasePermission):
    message = "Admin or Super Admin permission required."

    def has_permission(self, request, view):
        return has_any_role(
            request.user,
            [
                ROLE_SUPER_ADMIN,
                ROLE_ADMIN,
            ],
        )


class IsOperatorOrAbove(BasePermission):
    message = "Operator, Admin, or Super Admin permission required."

    def has_permission(self, request, view):
        return has_any_role(
            request.user,
            [
                ROLE_SUPER_ADMIN,
                ROLE_ADMIN,
                ROLE_OPERATOR,
            ],
        )


class IsViewerOrAbove(BasePermission):
    message = "Authenticated VisionX role required."

    def has_permission(self, request, view):
        return has_any_role(
            request.user,
            [
                ROLE_SUPER_ADMIN,
                ROLE_ADMIN,
                ROLE_OPERATOR,
                ROLE_VIEWER,
            ],
        )


class HasOrganization(BasePermission):
    """
    Requires an authenticated user to belong to an organization.

    Super Admin is allowed without an organization because
    Super Admin is a system-level role.
    """

    message = "User is not assigned to an organization."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if is_super_admin(user):
            return True

        return user.organization_id is not None


class IsOrganizationAdminOrSuperAdmin(BasePermission):
    """
    Allows Admin and Super Admin users.

    Non-Super Admin users must also belong to an organization.
    """

    message = "Organization Admin or Super Admin permission required."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if is_super_admin(user):
            return True

        return (
            has_role(user, ROLE_ADMIN)
            and user.organization_id is not None
        )


class IsOrganizationOperatorOrAbove(BasePermission):
    """
    Allows Operator, Admin and Super Admin.

    Non-Super Admin users must belong to an organization.
    """

    message = "Organization Operator, Admin, or Super Admin permission required."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if is_super_admin(user):
            return True

        return (
            has_any_role(
                user,
                [
                    ROLE_ADMIN,
                    ROLE_OPERATOR,
                ],
            )
            and user.organization_id is not None
        )


class IsOrganizationViewerOrAbove(BasePermission):
    """
    Allows Viewer, Operator, Admin and Super Admin.

    Non-Super Admin users must belong to an organization.
    """

    message = "User must have a VisionX role and organization."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if is_super_admin(user):
            return True

        return (
            has_any_role(
                user,
                [
                    ROLE_ADMIN,
                    ROLE_OPERATOR,
                    ROLE_VIEWER,
                ],
            )
            and user.organization_id is not None
        )
