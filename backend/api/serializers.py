from django.contrib.auth import get_user_model

from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from backend.constants import AMOUNT_MIN_VALUE
from recipes.models import Follow, Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()


class BaseUserSerializer(DjoserUserSerializer):
    """Сериализатор пользователя с полем подписки и аватаром."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = (*DjoserUserSerializer.Meta.fields, "avatar", "is_subscribed")

    def get_is_subscribed(self, user_instance):
        """Возвращает True, если текущий пользователь подписан на автора."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return (
            user
            and user.is_authenticated
            and Follow.objects.filter(
                user=user, following=user_instance
            ).exists()
        )


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели тега."""

    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели ингредиента."""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Отображает ингредиенты рецепта при чтении."""

    id = serializers.IntegerField(source="ingredient.id")
    name = serializers.CharField(source="ingredient.name")
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    """Создаёт ингредиенты рецепта при записи."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source="ingredient"
    )
    amount = serializers.IntegerField(min_value=AMOUNT_MIN_VALUE)

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount")


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор чтения рецептов."""

    author = BaseUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        source="recipeingredients", many=True, read_only=True
    )
    image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "author",
            "name",
            "image",
            "text",
            "tags",
            "ingredients",
            "cooking_time",
            "is_favorited",
            "is_in_shopping_cart",
        )

    def get_image(self, obj):
        """Возвращает абсолютный URL изображения рецепта."""
        request = self.context.get("request")
        if obj.image and hasattr(obj.image, "url"):
            return request.build_absolute_uri(obj.image.url)
        return ""

    def get_is_favorited(self, recipe):
        """Возвращает True, если рецепт добавлен в избранное."""
        user = self.context["request"].user
        return (
            user.is_authenticated
            and recipe.favorites.filter(user=user).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        """Возвращает True, если рецепт в списке покупок."""
        user = self.context["request"].user
        return (
            user.is_authenticated
            and recipe.shopping_cart.filter(user=user).exists()
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор создания и редактирования рецептов."""

    ingredients = RecipeIngredientWriteSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            "ingredients",
            "tags",
            "image",
            "name",
            "text",
            "cooking_time",
        )

    def validate_image(self, image):
        """Проверяет, что изображение нельзя очистить при редактировании."""
        request = self.context.get("request")
        method = getattr(request, "method", "").upper()
        if method in ("PUT", "PATCH") and image in (None, "", []):
            raise serializers.ValidationError(
                "Нельзя удалить изображение рецепта."
            )
        return image

    def validate(self, data):
        """Проверяет обязательные поля и наличие изображения при создании."""
        request = self.context.get("request")
        method = getattr(request, "method", "").upper()

        if method == "POST" and not data.get("image"):
            raise serializers.ValidationError(
                {"image": "Изображение обязательно для нового рецепта."}
            )

        for field in ("ingredients", "tags"):
            if not data.get(field):
                raise serializers.ValidationError(
                    {field: "Это поле обязательно."}
                )
        return data

    def validate_ingredients(self, ingredients):
        """Проверяет ингредиенты на дубли."""
        ids = [item["ingredient"].id for item in ingredients]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "Список ингредиентов содержит дубликаты."
            )
        return ingredients

    def validate_tags(self, tags):
        """Проверяет теги на дубли."""
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                "Список тегов содержит дубликаты."
            )
        return tags

    def _set_ingredients(self, recipe, ingredients):
        """Создаёт связи ингредиентов с рецептом."""
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=item["ingredient"],
                amount=item["amount"],
            )
            for item in ingredients
        )

    def create(self, validated_data):
        """Создаёт рецепт с тегами и ингредиентами."""
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self._set_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        """Обновляет рецепт и связанные объекты."""
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("ingredients")
        instance.tags.set(tags)
        instance.recipeingredients.all().delete()
        self._set_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Возвращает сериализатор чтения после сохранения."""
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeShortSerializer(serializers.ModelSerializer):
    """Короткий вариант рецепта для вложенных списков."""

    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")

    def get_image(self, obj):
        """Возвращает абсолютный URL изображения рецепта."""
        request = self.context.get("request")
        if obj.image and hasattr(obj.image, "url"):
            return request.build_absolute_uri(obj.image.url)
        return ""


class UserFollowSerializer(BaseUserSerializer):
    """Сериализатор авторов, на которых подписан пользователь."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source="recipes.count", read_only=True
    )

    class Meta(BaseUserSerializer.Meta):
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "avatar",
            "is_subscribed",
            "recipes",
            "recipes_count",
        )

    def get_recipes(self, user):
        """Возвращает рецепты автора с ограничением recipes_limit."""
        request = self.context.get("request")
        limit = request.GET.get("recipes_limit") if request else None
        recipes_qs = user.recipes.all()
        if limit and str(limit).isdigit():
            recipes_qs = recipes_qs[: int(limit)]
        return RecipeShortSerializer(
            recipes_qs, many=True, context=self.context
        ).data
