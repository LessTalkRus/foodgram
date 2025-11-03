from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from api.filters import IngredientSearchFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    BaseUserSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeShortSerializer,
    RecipeWriteSerializer,
    TagSerializer,
    UserFollowSerializer,
)
from recipes.models import (
    Favorite,
    Follow,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)

User = get_user_model()


# ===============================
# 👤 Пользователи
# ===============================


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = BaseUserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(
        detail=False,
        methods=["get"],
        url_path="me",
        permission_classes=[AllowAny],
    )
    def me(self, request):
        """Информация о текущем пользователе.
        Без токена возвращаем 401 вместо 500.
        """
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["put", "delete"],
        url_path="me/avatar",
        permission_classes=[IsAuthenticated],
    )
    def avatar(self, request):
        user = request.user

        if request.method == "PUT":
            avatar = request.data.get("avatar")
            if not avatar:
                raise ValidationError({"avatar": ["Это поле обязательно."]})

            serializer = self.get_serializer(
                instance=user,
                data={"avatar": avatar},
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"avatar": user.avatar.url}, status=status.HTTP_200_OK
            )

        # DELETE
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, pk=id)
        user = request.user

        if request.method == "DELETE":
            follow = Follow.objects.filter(user=user, following=author)
            if not follow.exists():
                raise ValidationError("Вы не подписаны на этого пользователя.")
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if user == author:
            raise ValidationError("Нельзя подписаться на самого себя.")
        if Follow.objects.filter(user=user, following=author).exists():
            raise ValidationError("Вы уже подписаны на этого пользователя.")

        Follow.objects.create(user=user, following=author)
        serializer = UserFollowSerializer(author, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        authors = User.objects.filter(
            id__in=Follow.objects.filter(user=request.user).values_list(
                "following", flat=True
            )
        )
        page = self.paginate_queryset(authors)
        if page is not None:
            serializer = UserFollowSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = UserFollowSerializer(
            authors, many=True, context={"request": request}
        )
        return Response(serializer.data)


# ===============================
# 🏷️ Теги
# ===============================


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


# ===============================
# 🧂 Ингредиенты
# ===============================


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = IngredientSearchFilter
    search_fields = ["^name"]
    ordering_fields = ["name"]
    permission_classes = [AllowAny]
    pagination_class = None


# ===============================
# 🍽️ Рецепты
# ===============================


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related("author").prefetch_related(
        "tags", "recipe_ingredients__ingredient"
    )
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = RecipeFilter
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    # ---------- Избранное / корзина ----------
    def _toggle_relation(self, model, recipe_id, request):
        recipe = get_object_or_404(Recipe, pk=recipe_id)

        if request.method == "DELETE":
            obj = model.objects.filter(user=request.user, recipe=recipe)
            if not obj.exists():
                raise ValidationError("Рецепт не найден в списке.")
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if model.objects.filter(user=request.user, recipe=recipe).exists():
            raise ValidationError("Рецепт уже добавлен.")
        model.objects.create(user=request.user, recipe=recipe)

        serializer = RecipeShortSerializer(
            recipe, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post", "delete"], url_path="favorite")
    def favorite(self, request, pk=None):
        return self._toggle_relation(Favorite, pk, request)

    @action(detail=True, methods=["post", "delete"], url_path="shopping_cart")
    def shopping_cart(self, request, pk=None):
        return self._toggle_relation(ShoppingCart, pk, request)

    # ---------- Список покупок ----------
    @action(
        detail=False,
        methods=["get"],
        url_path="download_shopping_cart",
        permission_classes=[IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        user = request.user
        recipes = Recipe.objects.filter(shopping_cart__user=user)

        ingredients = (
            RecipeIngredient.objects.filter(recipe__in=recipes)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        content = render_to_string(
            "shopping_cart_list.txt",
            {
                "user": user,
                "date": now().date(),
                "ingredients": ingredients,
                "recipes": recipes,
            },
        )

        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = (
            'attachment; filename="shopping_cart_list.txt"'
        )
        return response

    # ---------- Короткая ссылка ----------
    @action(
        detail=True,
        methods=["get"],
        url_path="get-link",
        permission_classes=[AllowAny],
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        try:
            detail_url = request.build_absolute_uri(
                reverse("recipe-detail", kwargs={"pk": recipe.id})
            )
        except Exception:
            # fallback — прямой путь без reverse
            detail_url = request.build_absolute_uri(
                f"/api/recipes/{recipe.id}/"
            )
        return Response({"short-link": detail_url}, status=status.HTTP_200_OK)
