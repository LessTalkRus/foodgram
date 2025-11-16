from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

from backend.constants import (
    AMOUNT_MIN_VALUE,
    INGREDIENT_LENGTH,
    MEASURE_LENGTH,
    MIN_COOK_TIME,
    TAG_LENGTH,
)

User = get_user_model()


class Tag(models.Model):
    """
    Модель тега, который используется для классификации рецептов.

    Тег содержит уникальные поля `name` и `slug` и применяется для
    фильтрации рецептов по категориям.
    """

    name = models.CharField(
        max_length=TAG_LENGTH, unique=True, verbose_name="Название тега"
    )
    slug = models.SlugField(
        max_length=TAG_LENGTH, unique=True, verbose_name="Слаг тега"
    )

    class Meta:
        """Мета-параметры модели Tag."""

        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("name", "slug"), name="unique_tags"
            )
        ]

    def __str__(self):
        """Возвращает строковое представление тега (его имя)."""
        return self.name


class Ingredient(models.Model):
    """
    Модель ингредиента, используемого в рецептах.

    Хранит название ингредиента и единицу измерения. Названия ингредиентов
    индексируются для ускоренного поиска.
    """

    name = models.CharField(
        max_length=INGREDIENT_LENGTH,
        db_index=True,
        verbose_name="Название ингредиента",
    )
    measurement_unit = models.CharField(
        max_length=MEASURE_LENGTH, verbose_name="Единица измерения"
    )

    class Meta:
        """Мета-параметры модели Ingredient."""

        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        constraints = [
            models.UniqueConstraint(
                fields=("name", "measurement_unit"), name="unique_ingredient"
            )
        ]
        ordering = ("name",)

    def __str__(self):
        """Возвращает строковое представление ингредиента."""
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    """
    Модель рецепта.

    Содержит информацию о названии, тексте, времени приготовления,
    ингредиентах, тегах и авторе. Используется связь ManyToMany для
    ингредиентов и тегов.
    """

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="Автор рецепта"
    )
    name = models.CharField(max_length=200, verbose_name="Название рецепта")
    image = models.ImageField(
        verbose_name="Изображение",
        upload_to="recipes/images",
        null=True,
        blank=True,
    )
    text = models.TextField(verbose_name="Описание рецепта")
    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredient", verbose_name="Ингредиенты"
    )
    tags = models.ManyToManyField(Tag, verbose_name="Теги")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата создания"
    )
    cooking_time = models.PositiveIntegerField(
        validators=[
            MinValueValidator(
                MIN_COOK_TIME,
                "Минимальное значение - {MIN_COOK_TIME} минут(а).",
            )
        ],
        verbose_name="Время приготовления, мин.",
    )

    class Meta:
        """Мета-параметры модели Recipe."""

        default_related_name = "recipes"
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        ordering = ("-created_at",)

    def __str__(self):
        """Возвращает строковое представление рецепта (его имя)."""
        return self.name


class RecipeIngredient(models.Model):
    """
    Промежуточная модель для связи рецептов и ингредиентов.

    Хранит количество каждого ингредиента, необходимого для рецепта.
    """

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name="Рецепт",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name="Ингредиент",
    )
    amount = models.PositiveIntegerField(
        verbose_name="Количество",
        validators=[
            MinValueValidator(
                AMOUNT_MIN_VALUE,
                "Минимальное количество - {AMOUNT_MIN_VALUE}."
            )
        ],
    )

    class Meta:
        """Мета-параметры модели RecipeIngredient."""

        default_related_name = "recipeingredients"
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецептах"
        constraints = [
            models.UniqueConstraint(
                fields=("recipe", "ingredient"),
                name="unique_ingredients_in_the_recipe",
            )
        ]

    def __str__(self):
        """Возвращает строковое представление ингредиента в рецепте."""
        return f"{self.ingredient.name} в {self.recipe.name} - {self.amount}"


class BaseRecipeUserModel(models.Model):
    """
    Абстрактная модель для связи пользователя и рецепта.

    Используется как основа для избранного и списка покупок.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="Пользователь"
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, verbose_name="Рецепт"
    )

    class Meta:
        """Мета-параметры базовой модели связи User–Recipe."""

        abstract = True
        ordering = ("user", "recipe")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="%(class)rs_unique_user_recipe"
            )
        ]

    def __str__(self):
        """Возвращает строковое представление связи User–Recipe."""
        return f"{self.user.username} - {self.recipe.name}"


class Favorite(BaseRecipeUserModel):
    """
    Модель для хранения рецептов, добавленных пользователем в избранное.
    """

    class Meta(BaseRecipeUserModel.Meta):
        """Мета-параметры модели Favorite."""

        default_related_name = "favorites"
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"

    def __str__(self):
        """Возвращает строковое представление избранного рецепта."""
        return f"Рецепт {self.recipe.name} в избранном у {self.user.username}"


class ShoppingCart(BaseRecipeUserModel):
    """
    Модель списка покупок пользователя.

    Содержит рецепты, добавленные в корзину для последующего скачивания
    или оформления списка ингредиентов.
    """

    class Meta(BaseRecipeUserModel.Meta):
        """Мета-параметры модели ShoppingCart."""

        default_related_name = "shopping_carts"
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"

    def __str__(self):
        """Возвращает строковое представление записи корзины."""
        return f"{self.user.username} добавил в корзину {self.recipe.name}"


class Follow(models.Model):
    """
    Модель подписки пользователя на автора рецептов.

    Хранит связь между пользователем (подписчиком) и автором (following).
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="followers",
        verbose_name="Подписчик",
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="authors",
        verbose_name="Автор",
    )

    class Meta:
        """Мета-параметры модели Follow."""

        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "following"], name="unique_follow"
            )
        ]
        ordering = ("user__username", "following__username")

    def __str__(self):
        """Возвращает строковое представление подписки."""
        return f"{self.user.username} подписан на {self.following.username}"
