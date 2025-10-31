from typing import List

import base64
from django.db import transaction
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import (
    Tag, Ingredient, Recipe, RecipeIngredient,
    Favorite, ShoppingCart, Follow
)
from users.models import User


# ---------- Базовые сериализаторы ----------

class Base64ImageField(serializers.ImageField):
    """Принимает картинку в base64, сохраняет как ImageField."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            # data:image/png;base64,xxxx
            format_, imgstr = data.split(';base64,')
            ext = format_.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'upload.{ext}')
        return super().to_internal_value(data)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


# ---------- Пользователи ----------

class CustomUserSerializer(serializers.ModelSerializer):
    """Пользователь + признак подписки на него текущего юзера."""
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj) -> bool:
        user = self.context.get('request').user
        if not user or user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, author=obj).exists()


# ---------- Рецепты ----------

class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Ингредиент в составе рецепта (для чтения)."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeIngredientWriteSerializer(serializers.Serializer):
    """Ингредиент при создании/обновлении рецепта."""
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)

    def validate_id(self, value):
        if not Ingredient.objects.filter(id=value).exists():
            raise serializers.ValidationError('Ингредиент с таким id не найден.')
        return value


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Короткий рецепт (для избранного/корзины, подписок и т.п.)."""
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Выдача рецепта наружу."""
    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientReadSerializer(source='recipe_ingredients', many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time',
        )

    def get_is_favorited(self, obj) -> bool:
        user = self.context.get('request').user
        if not user or user.is_anonymous:
            return False
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj) -> bool:
        user = self.context.get('request').user
        if not user or user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Создание/обновление рецепта."""
    ingredients = RecipeIngredientWriteSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = ('id', 'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time')

    def validate_cooking_time(self, value: int) -> int:
        if value < 1:
            raise serializers.ValidationError('Время приготовления должно быть >= 1.')
        return value

    def validate_tags(self, value: List[Tag]) -> List[Tag]:
        if not value:
            raise serializers.ValidationError('Добавьте хотя бы один тег.')
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Теги не должны повторяться.')
        return value

    def validate_ingredients(self, value: List[dict]) -> List[dict]:
        if not value:
            raise serializers.ValidationError('Добавьте хотя бы один ингредиент.')
        seen = set()
        for item in value:
            ing_id = item['id']
            if ing_id in seen:
                raise serializers.ValidationError('Ингредиенты не должны повторяться.')
            seen.add(ing_id)
            if item['amount'] < 1:
                raise serializers.ValidationError('Количество ингредиента должно быть >= 1.')
        return value

    @staticmethod
    def _set_ingredients(recipe: Recipe, ingredients_data: List[dict]):
        RecipeIngredient.objects.filter(recipe=recipe).delete()
        bulk = []
        for item in ingredients_data:
            ingredient = Ingredient.objects.get(id=item['id'])
            bulk.append(RecipeIngredient(recipe=recipe, ingredient=ingredient, amount=item['amount']))
        RecipeIngredient.objects.bulk_create(bulk)

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(author=self.context['request'].user, **validated_data)
        recipe.tags.set(tags)
        self._set_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance: Recipe, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if tags is not None:
            instance.tags.set(tags)
        instance.save()
        if ingredients is not None:
            self._set_ingredients(instance, ingredients)
        return instance

    def to_representation(self, instance):
        # После create/update возвращаем полное представление рецепта
        return RecipeReadSerializer(instance, context=self.context).data
