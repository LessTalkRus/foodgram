from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Кастомная админка для модели User.

    Поддерживает смену пароля и редактирование дополнительных полей
    (avatar и других пользовательских атрибутов).
    """

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Персональная информация"),
            {"fields": ("username", "first_name", "last_name", "avatar")},
        ),
        (
            _("Права доступа"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Важные даты"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    list_display = (
        "id",
        "email",
        "username",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    search_fields = ("email", "username", "first_name", "last_name")
    list_filter = ("is_staff", "is_superuser", "is_active")
    ordering = ("id",)
    list_display_links = ("id", "username")
    empty_value_display = "-пусто-"
