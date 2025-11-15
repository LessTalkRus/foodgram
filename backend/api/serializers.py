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
        fields = (*DjoserUserSerializer.Meta.fields,
                  "avatar",
                  "is_subscribed")

    def get_is_subscribed(self, user_instance):
        """Проверяет подписку на автора через related_name=followers."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return (
            user
            and user.is_authenticated
            and user.followers.filter(following=user_instance).exists()
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
    amount = serializers.IntegerField(
        min_value=AMOUNT_MIN_VALUE,
        max_value=10000  # разумный максимум
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount")


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор чтения рецептов."""

    author = BaseUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        source="recipeingredients",
        many=True,
        read_only=True
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
        return (
            request.build_absolute_uri(obj.image.url)
            if obj.image and hasattr(obj.image, "url")
            else ""
        )

    def _check_relation(self, manager):
        """Универсальная проверка избранного/корзины."""
        user = self.context["request"].user
        return user.is_authenticated and manager.filter(user=user).exists()

    def get_is_favorited(self, recipe):
        return self._check_relation(recipe.favorites)

    def get_is_in_shopping_cart(self, recipe):
        return self._check_relation(recipe.shopping_carts)


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор создания и редактирования рецептов."""

    ingredients = RecipeIngredientWriteSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField()

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
        """Общая валидация: изображение, теги, ингредиенты."""
        ingredients = data.get("ingredients")
        tags = data.get("tags")

        if not data.get("image"):
            raise serializers.ValidationError(
                {"image": "Картинка обязательное поле для рецепта."}
            )

        if not ingredients:
            raise serializers.ValidationError(
                {"ingredients": "Это поле обязательно."}
            )

        if not tags:
            raise serializers.ValidationError(
                {"tags": "Это поле обязательно."}
            )

        # проверка дублей ингредиентов
        ingredient_ids = [item["ingredient"].id for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {"ingredients": "Список ингредиентов содержит дубликаты."}
            )

        # проверка дублей тегов
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                {"tags": "Список тегов содержит дубликаты."}
            )

        return data

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
        tags = validated_data.pop("tags", None)
        ingredients = validated_data.pop("ingredients", None)

        if tags is not None:
            instance.tags.set(tags)

        if ingredients is not None:
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
        request = self.context.get("request")
        return (
            request.build_absolute_uri(obj.image.url)
            if obj.image and hasattr(obj.image, "url")
            else ""
        )


class UserFollowSerializer(BaseUserSerializer):
    """Сериализатор авторов, на которых подписан пользователь."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source="recipes.count", read_only=True
    )

    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields + (
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
            recipes_qs,
            many=True,
            context=self.context,
        ).data
