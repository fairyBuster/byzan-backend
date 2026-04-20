from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "email",
        "username",
        "full_name",
        "phone",
        "is_active",
        "is_staff",
        "date_joined",
        "balance",
    )
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "username", "full_name", "phone")
    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Profile",
            {
                "fields": (
                    "gender",
                    "birthday",
                    "full_name",
                    "phone",
                    "address",
                    "city",
                    "state",
                    "country",
                    "pincode",
                    "instagram_link",
                    "facebook_link",
                    "email_verified",
                    "balance",
                )
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            None,
            {
                "fields": (
                    "email",
                    "username",
                    "full_name",
                    "phone",
                    "password1",
                    "password2",
                )
            },
        ),
    )
