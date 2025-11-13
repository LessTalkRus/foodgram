from django_filters import rest_framework as filters
from recipes.models import Ingredient, Recipe


class RecipeFilter(filters.FilterSet):
    """Фильтры для модели рецепта."""

    is_favorited = filters.BooleanFilter(method="filter_is_favorited")
    is_in_shopping_cart = filters.BooleanFilter(
        method="filter_is_in_shopping_cart"
    )
    tags = filters.AllValuesMultipleFilter(field_name="tags__slug")

    class Meta:
        model = Recipe
        fields = ("author", "tags", "is_favorited", "is_in_shopping_cart")

    def filter_is_favorited(self, queryset, name, value):
        """Возвращает рецепты, добавленные пользователем в избранное."""
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorites__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Возвращает рецепты, находящиеся в корзине пользователя."""
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shopping_cart__user=user)
        return queryset


class IngredientSearchFilter(filters.FilterSet):
    """Фильтр для поиска ингредиентов по началу имени."""

    name = filters.CharFilter(method="filter_name_startswith")

    class Meta:
        model = Ingredient
        fields = ("name",)

    def filter_name_startswith(self, queryset, name, value):
        """Фильтрует ингредиенты по первым буквам названия."""
        if not value:
            return queryset
        return queryset.filter(name__istartswith=value).order_by("name")
