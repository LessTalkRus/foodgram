from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

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


# ---------- Inline для ингредиентов ----------
class RecipeIngredientInlineFormSet(forms.BaseInlineFormSet):
    """Валидация ингредиентов в админке рецептов."""

    def clean(self):
        super().clean()
        has_ingredient = any(
            form.cleaned_data
            and not form.cleaned_data.get("DELETE", False)
            for form in self.forms
        )
        if not has_ingredient:
            raise ValidationError("Выберите хотя бы один ингредиент.")


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    formset = RecipeIngredientInlineFormSet
    extra = 1
    min_num = 1
    validate_min = True


# ---------- Inline для тегов ----------
class TagInlineFormSet(forms.BaseInlineFormSet):
    """Валидация тегов в админке рецептов."""

    def clean(self):
        super().clean()
        has_tag = any(
            form.cleaned_data
            and not form.cleaned_data.get("DELETE", False)
            for form in self.forms
        )
        if not has_tag:
            raise ValidationError("Выберите хотя бы один тег.")


class TagInline(admin.TabularInline):
    model = Recipe.tags.through
    formset = TagInlineFormSet
    extra = 1
    min_num = 1
    validate_min = True


# ---------- Админка моделей ----------
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
    inlines = [TagInline, RecipeIngredientInline]

    @admin.display(description="Добавлен в избранное")
    def get_favorites_count(self, obj):
        """Количество добавлений рецепта в избранное."""
        return obj.favorites.count()

    @admin.display(description="Теги")
    def get_tags(self, obj):
        """Возвращает список тегов рецепта, разделённых запятой."""
        return ", ".join(tag.name for tag in obj.tags.all())

    def save_model(self, request, obj, form, change):
        """Переопределение сохранения для отображения ошибок inline."""
        try:
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            self.message_user(
                request,
                f"Ошибка при сохранении рецепта: {e}",
                level=messages.ERROR,
            )
            raise


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
