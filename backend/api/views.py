from collections import defaultdict

from django.db.models import Q, Sum, F
from django.http import HttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from users.models import User
from recipes.models import Tag, Ingredient, Recipe, Favorite, ShoppingCart, Follow, RecipeIngredient
from api.serializers import (
    CustomUserSerializer, TagSerializer, IngredientSerializer,
    RecipeReadSerializer, RecipeWriteSerializer, ShortRecipeSerializer
)
from api.filters import RecipeFilter
from api.pagination import CustomPagination


# ---------- Users ----------

class UserViewSet(viewsets.ModelViewSet):
    """Пользователи + подписки (как у тебя было), теперь доступны все методы."""
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = CustomPagination

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = self.get_object()
        user = request.user

        if request.method == 'POST':
            if user == author:
                return Response({'detail': 'Нельзя подписаться на самого себя.'}, status=status.HTTP_400_BAD_REQUEST)
            if Follow.objects.filter(user=user, author=author).exists():
                return Response({'detail': 'Вы уже подписаны.'}, status=status.HTTP_400_BAD_REQUEST)
            Follow.objects.create(user=user, author=author)
            data = CustomUserSerializer(author, context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        Follow.objects.filter(user=user, author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        authors = User.objects.filter(followers__user=request.user).distinct()
        page = self.paginate_queryset(authors)
        serializer = CustomUserSerializer(page or authors, many=True, context={'request': request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


# ---------- Tags & Ingredients ----------

class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        if not name:
            return qs
        # сначала начинается с, потом содержит
        starts = qs.filter(name__istartswith=name)
        rest = qs.filter(~Q(pk__in=starts.values('pk')), name__icontains=name)
        return starts.union(rest)


# ---------- Recipes ----------

class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related('tags', 'recipe_ingredients__ingredient')
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method in ('POST', 'PUT', 'PATCH'):
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    # --- избранное ---

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        if Favorite.objects.filter(user=request.user, recipe=recipe).exists():
            return Response({'detail': 'Рецепт уже в избранном.'}, status=status.HTTP_400_BAD_REQUEST)
        Favorite.objects.create(user=request.user, recipe=recipe)
        return Response(ShortRecipeSerializer(recipe, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def unfavorite(self, request, pk=None):
        recipe = self.get_object()
        deleted, _ = Favorite.objects.filter(user=request.user, recipe=recipe).delete()
        if not deleted:
            return Response({'detail': 'Этого рецепта нет в избранном.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- корзина покупок ---

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        if ShoppingCart.objects.filter(user=request.user, recipe=recipe).exists():
            return Response({'detail': 'Рецепт уже в списке покупок.'}, status=status.HTTP_400_BAD_REQUEST)
        ShoppingCart.objects.create(user=request.user, recipe=recipe)
        return Response(ShortRecipeSerializer(recipe, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def remove_from_cart(self, request, pk=None):
        recipe = self.get_object()
        deleted, _ = ShoppingCart.objects.filter(user=request.user, recipe=recipe).delete()
        if not deleted:
            return Response({'detail': 'Этого рецепта нет в списке покупок.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- скачать список покупок ---

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        """Суммирует количества ингредиентов по всем рецептам в корзине и отдаёт txt."""
        # Через агрегирование по Ingredient
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shopping_cart__user=request.user)
            .values(name=F('ingredient__name'), unit=F('ingredient__measurement_unit'))
            .annotate(total=Sum('amount'))
            .order_by('name')
        )

        if not ingredients:
            return Response({'detail': 'Список покупок пуст.'}, status=status.HTTP_400_BAD_REQUEST)

        lines = ['Список покупок:\n']
        for item in ingredients:
            lines.append(f"- {item['name']} — {item['total']} {item['unit']}")

        content = '\n'.join(lines) + '\n'
        response = HttpResponse(content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename=shopping_list.txt'
        return response
