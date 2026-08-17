from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "mobile",
        "is_phone_verified",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "mobile",
    )
    list_filter = (
        "is_phone_verified",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
