from io import BytesIO

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (
    SAFE_METHODS,
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


class UserViewSet(DjoserUserViewSet):
    """ViewSet для управления пользователями и их действиями."""

    queryset = User.objects.all()
    serializer_class = BaseUserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(
        detail=False,
        methods=["get"],
        url_path="me",
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        """Возвращает данные текущего пользователя."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["put", "delete"],
        url_path="me/avatar",
        permission_classes=[IsAuthenticated],
    )
    def avatar(self, request):
        """Загружает или удаляет аватар пользователя."""
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
        """Подписывает или отписывает пользователя от автора."""
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
    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        """Возвращает список авторов, на которых подписан пользователь."""
        authors = User.objects.filter(
            id__in=Follow.objects.filter(user=request.user).values_list(
                "following", flat=True
            )
        )
        page = self.paginate_queryset(authors)
        serializer = UserFollowSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Просмотр тегов без возможности редактирования."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Просмотр ингредиентов с возможностью поиска по имени."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = IngredientSearchFilter
    search_fields = ["^name"]
    ordering_fields = ["name"]
    permission_classes = [AllowAny]
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """CRUD для рецептов с дополнительными действиями."""

    queryset = Recipe.objects.select_related("author").prefetch_related(
        "tags", "recipeingredients__ingredient"
    )
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = RecipeFilter
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_serializer_class(self):
        """Определяет сериализатор в зависимости от метода запроса."""
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        """Сохраняет рецепт, устанавливая автора текущим пользователем."""
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        """Разрешает частичное обновление рецепта."""
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    def get_serializer_context(self):
        """Добавляет объект запроса в контекст сериализатора."""
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def _toggle_relation(self, model, recipe_id, user, request):
        """Добавляет или удаляет рецепт в связанной модели."""
        recipe = get_object_or_404(Recipe, pk=recipe_id)

        if request.method == "DELETE":
            deleted_count, _ = model.objects.filter(
                user=user, recipe=recipe
            ).delete()

            if deleted_count == 0:
                raise ValidationError("Рецепт не найден в списке.")

            return Response(status=status.HTTP_204_NO_CONTENT)

        if model.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError("Рецепт уже добавлен.")

        model.objects.create(user=user, recipe=recipe)

        serializer = RecipeShortSerializer(
            recipe, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post", "delete"], url_path="favorite")
    def favorite(self, request, pk=None):
        """Добавляет или удаляет рецепт из избранного."""
        return self._toggle_relation(Favorite, pk, request.user, request)

    @action(detail=True, methods=["post", "delete"], url_path="shopping_cart")
    def shopping_cart(self, request, pk=None):
        """Добавляет или удаляет рецепт из списка покупок."""
        return self._toggle_relation(ShoppingCart, pk, request.user, request)

    def _generate_shopping_cart_text(self, user):
        """Генерирует текстовый список покупок для пользователя."""
        recipes = Recipe.objects.filter(shopping_cart__user=user)

        ingredients = (
            RecipeIngredient.objects.filter(recipe__in=recipes)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        return render_to_string(
            "shopping_cart_list.txt",
            {
                "user": user,
                "date": now().date(),
                "ingredients": ingredients,
                "recipes": recipes,
            },
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="download_shopping_cart",
        permission_classes=[IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        """Отдаёт список покупок через FileResponse."""
        text = self._generate_shopping_cart_text(request.user)

        buffer = BytesIO()
        buffer.write(text.encode("utf-8"))
        buffer.seek(0)

        return FileResponse(
            buffer,
            as_attachment=True,
            filename="shopping_cart_list.txt",
            content_type="text/plain",
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="get-link",
        permission_classes=[AllowAny],
    )
    def get_link(self, request, pk=None):
        """Возвращает короткую ссылку на рецепт."""
        recipe = get_object_or_404(Recipe, pk=pk)
        url = request.build_absolute_uri(f"/recipes/{recipe.id}/")
        return Response({"short-link": url}, status=status.HTTP_200_OK)
