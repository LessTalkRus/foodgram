from collections import Counter
from django.contrib.auth import get_user_model
from rest_framework import serializers
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (
    Tag, Ingredient, Recipe, RecipeIngredient,
    Favorite, ShoppingCart, Follow
)

User = get_user_model()


# ===============================
# 👤 Пользователи
# ===============================

class BaseUserSerializer(DjoserUserSerializer):
    """Базовый сериализатор пользователя с полем подписки и аватаром."""
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = (*DjoserUserSerializer.Meta.fields, 'avatar', 'is_subscribed')
        read_only_fields = ('is_subscribed',)

    # ✅ FIX: безопасная проверка user для анонимов
    def get_is_subscribed(self, user_instance):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return Follow.objects.filter(user=user, following=user_instance).exists()

    def create(self, validated_data):
        """Позволяет создавать пользователя без поля re_password."""
        user = User.objects.create_user(**validated_data)
        return user


# ===============================
# 🏷 Теги и ингредиенты
# ===============================

class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


# ===============================
# 🍳 Ингредиенты в рецептах
# ===============================

class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Отображение ингредиентов в рецепте (чтение)."""
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = fields


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    """Создание ингредиентов в рецепте (запись)."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


# ===============================
# 🍽️ Рецепты
# ===============================

class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""
    author = BaseUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'image', 'text',
            'tags', 'ingredients', 'cooking_time',
            'is_favorited', 'is_in_shopping_cart'
        )
        read_only_fields = fields

    # ✅ FIX: безопасная проверка user
    def _check_relation(self, model, recipe):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return (
            user and user.is_authenticated and
            model.objects.filter(user=user, recipe=recipe).exists()
        )

    def get_is_favorited(self, recipe):
        return self._check_relation(Favorite, recipe)

    def get_is_in_shopping_cart(self, recipe):
        return self._check_relation(ShoppingCart, recipe)


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/редактирования рецептов."""
    ingredients = RecipeIngredientWriteSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'image', 'name', 'text', 'cooking_time')

    # ✅ FIX: проверка обязательных полей
    def validate(self, data):
        if not data.get('ingredients'):
            raise serializers.ValidationError({'ingredients': 'Это поле обязательно.'})
        if not data.get('tags'):
            raise serializers.ValidationError({'tags': 'Это поле обязательно.'})
        if not data.get('image'):
            raise serializers.ValidationError({'image': 'Это поле обязательно.'})
        return data

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError('Список ингредиентов не может быть пустым.')
        ids = [item['ingredient'].id for item in ingredients]
        duplicates = [i for i, count in Counter(ids).items() if count > 1]
        if duplicates:
            raise serializers.ValidationError(f'Дублируются ингредиенты с ID: {duplicates}')
        return ingredients

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError('Список тегов не может быть пустым.')
        duplicates = [i for i, count in Counter(tags).items() if count > 1]
        if duplicates:
            raise serializers.ValidationError(f'Дублируются теги с ID: {duplicates}')
        return tags

    def _set_ingredients(self, recipe, ingredients):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            ) for item in ingredients
        ])

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self._set_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        if tags is not None:
            instance.tags.set(tags)
        if ingredients is not None:
            instance.recipe_ingredients.all().delete()
            self._set_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """После сохранения вернуть сериализатор чтения."""
        return RecipeReadSerializer(instance, context=self.context).data


# ===============================
# 🧩 Короткий вид рецепта
# ===============================

class RecipeShortSerializer(serializers.ModelSerializer):
    """Укороченный вариант рецепта (для избранного, подписок и корзины)."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


# ===============================
# 🔔 Подписки пользователей
# ===============================

class UserFollowSerializer(BaseUserSerializer):
    """Сериализатор отображения авторов, на которых подписан пользователь."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes.count', read_only=True)

    class Meta(BaseUserSerializer.Meta):
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'avatar', 'is_subscribed', 'recipes', 'recipes_count'
        )
        read_only_fields = fields

    def get_recipes(self, user):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit') if request else None
        recipes_qs = user.recipes.all()
        if limit and str(limit).isdigit():
            recipes_qs = recipes_qs[:int(limit)]
        return RecipeShortSerializer(recipes_qs, many=True, context=self.context).data
