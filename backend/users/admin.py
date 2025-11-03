from django.contrib import admin

from users.models import User

admin.site.empty_value_display = "-пусто-"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Настройка отображения и редактирования пользователей в админ-панели.

    Определяет поля, отображаемые в списке, поиск, фильтрацию и порядок
    сортировки записей.
    """

    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("is_staff", "is_superuser", "is_active")
    ordering = ("id",)
    list_editable = ("is_staff",)
    list_display_links = ("id", "username")

    fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "avatar",
        "is_staff",
        "is_superuser",
        "is_active",
        "password",
    )
