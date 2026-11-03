from django.db.models import QuerySet


def organization_queryset(queryset: QuerySet, user, field="organization"):
    """
    Restrict a queryset to the authenticated user's organization.

    Super Admin:
        Can access all organizations.

    Other users:
        Can access only records belonging to their organization.

    Users without an organization:
        Receive an empty queryset.
    """

    if not user or not user.is_authenticated:
        return queryset.none()

    if user.groups.filter(name="Super Admin").exists():
        return queryset

    organization_id = getattr(user, "organization_id", None)

    if not organization_id:
        return queryset.none()

    return queryset.filter(**{f"{field}_id": organization_id})
