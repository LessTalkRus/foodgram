from django.contrib import admin

from recipes.models import (
    Favorite,
    Follow,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)

admin.site.empty_value_display = "-пусто-"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Управление тегами в административной панели."""

    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Управление ингредиентами в административной панели."""

    list_display = ("name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("name",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Управление рецептами в административной панели."""

    list_display = ("name", "author", "get_favorites_count", "get_tags")
    search_fields = ("name", "author__username")
    list_filter = ("author", "name", "tags")

    def get_favorites_count(self, obj):
        """Возвращает количество добавлений рецепта в избранное."""
        return obj.favorites.count()

    def get_tags(self, obj):
        """Возвращает список тегов рецепта, разделённых запятой."""
        return ", ".join(tag.name for tag in obj.tags.all())

    get_favorites_count.short_description = "Добавлен в избранное"
    get_tags.short_description = "Теги"


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    """Управление ингредиентами, используемыми в рецептах."""

    list_display = ("recipe", "ingredient", "amount")
    list_filter = ("recipe", "ingredient")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Управление подписками пользователей."""

    list_display = ("user", "following")
    search_fields = ("user__username", "following__username")
    list_filter = ("user", "following")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Управление избранными рецептами пользователей."""

    list_display = ("user", "recipe")
    list_filter = ("user", "recipe")


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """Управление списками покупок пользователей."""

    list_display = ("user", "recipe")
    list_filter = ("user", "recipe")
