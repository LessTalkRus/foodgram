from collections import Counter

from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

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


class BaseUserSerializer(DjoserUserSerializer):
    """Сериализатор пользователя с полем подписки и аватаром."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = (*DjoserUserSerializer.Meta.fields, "avatar", "is_subscribed")
        read_only_fields = ("is_subscribed",)

    def get_is_subscribed(self, user_instance):
        """Возвращает True, если текущий пользователь подписан на автора."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return Follow.objects.filter(
            user=user, following=user_instance
        ).exists()

    def create(self, validated_data):
        """Создаёт пользователя без поля подтверждения пароля."""
        user = User.objects.create_user(**validated_data)
        return user


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
        read_only_fields = fields


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    """Создаёт ингредиенты рецепта при записи."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source="ingredient"
    )
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount")


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор чтения рецептов."""

    author = BaseUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        source="recipe_ingredients", many=True, read_only=True
    )
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
        read_only_fields = fields

    def _check_relation(self, model, recipe):
        """Проверяет наличие связи пользователя и рецепта."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return (
            user
            and user.is_authenticated
            and model.objects.filter(user=user, recipe=recipe).exists()
        )

    def get_is_favorited(self, recipe):
        """Возвращает True, если рецепт добавлен в избранное."""
        return self._check_relation(Favorite, recipe)

    def get_is_in_shopping_cart(self, recipe):
        """Возвращает True, если рецепт в списке покупок."""
        return self._check_relation(ShoppingCart, recipe)


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор создания и редактирования рецептов."""

    ingredients = RecipeIngredientWriteSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(required=True)

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

    def validate(self, data):
        """Проверяет наличие обязательных полей."""
        for field in ("ingredients", "tags", "image"):
            if not data.get(field):
                raise serializers.ValidationError(
                    {field: "Это поле обязательно."}
                )
        return data

    def validate_ingredients(self, ingredients):
        """Проверяет список ингредиентов на дубликаты и пустоту."""
        if not ingredients:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым."
            )
        ids = [item["ingredient"].id for item in ingredients]
        duplicates = [i for i, c in Counter(ids).items() if c > 1]
        if duplicates:
            raise serializers.ValidationError(
                f"Дублируются ингредиенты с ID: {duplicates}"
            )
        return ingredients

    def validate_tags(self, tags):
        """Проверяет список тегов на дубликаты и пустоту."""
        if not tags:
            raise serializers.ValidationError(
                "Список тегов не может быть пустым."
            )
        duplicates = [i for i, c in Counter(tags).items() if c > 1]
        if duplicates:
            raise serializers.ValidationError(
                f"Дублируются теги с ID: {duplicates}"
            )
        return tags

    def _set_ingredients(self, recipe, ingredients):
        """Создаёт связи ингредиентов с рецептом."""
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=item["ingredient"],
                    amount=item["amount"],
                )
                for item in ingredients
            ]
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
        tags = validated_data.pop("tags", None)
        ingredients = validated_data.pop("ingredients", None)
        if tags is not None:
            instance.tags.set(tags)
        if ingredients is not None:
            instance.recipe_ingredients.all().delete()
            self._set_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Возвращает сериализатор чтения после сохранения."""
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeShortSerializer(serializers.ModelSerializer):
    """Короткий вариант рецепта для вложенных списков."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields


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
        read_only_fields = fields

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
