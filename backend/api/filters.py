from django_filters import rest_framework as filters
from recipes.models import Ingredient, Recipe, Tag


class RecipeFilter(filters.FilterSet):
    """Фильтры для модели Recipe (рецепты)."""
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_is_in_shopping_cart')
    author = filters.NumberFilter(field_name='author__id', lookup_expr='exact')
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug',
    )

    class Meta:
        model = Recipe
        fields = ('is_favorited', 'is_in_shopping_cart', 'author', 'tags')

    def filter_is_favorited(self, queryset, name, value):
        """Фильтрация по признаку: рецепт в избранном у пользователя."""
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorites__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтрация по признаку: рецепт в корзине пользователя."""
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shopping_cart__user=user)
        return queryset


class IngredientSearchFilter(filters.FilterSet):
    """Поиск ингредиентов по началу названия (регистр не учитывается)."""
    name = filters.CharFilter(method='filter_name_startswith')

    class Meta:
        model = Ingredient
        fields = ('name',)

    def filter_name_startswith(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(name__istartswith=value).order_by('name')
