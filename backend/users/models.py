from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from backend.constants import EMAIL_LENGTH, NICKNAME_LENGTH, NAME_LENGTH


class User(AbstractUser):
    """Модель пользователя проекта Foodgram."""

    email = models.EmailField(
        max_length=EMAIL_LENGTH,
        unique=True,
        verbose_name="Электронная почта",
        help_text="Уникальный адрес электронной почты пользователя.",
    )
    username = models.CharField(
        max_length=NICKNAME_LENGTH,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        verbose_name="Имя пользователя",
        help_text=(
            "Имя пользователя. Может содержать буквы, цифры и символы "
            "@ . - _"
        ),
    )
    first_name = models.CharField(
        max_length=NAME_LENGTH,
        verbose_name="Имя",
        help_text="Имя пользователя.",
    )
    last_name = models.CharField(
        max_length=NAME_LENGTH,
        verbose_name="Фамилия",
        help_text="Фамилия пользователя.",
    )
    avatar = models.ImageField(
        upload_to="users/avatars/",
        blank=True,
        null=True,
        verbose_name="Аватар",
        help_text="Изображение профиля пользователя (необязательно).",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        """Мета-информация для модели пользователя."""

        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ("first_name",)

    def __str__(self):
        """Возвращает строковое представление пользователя (username)."""
        return self.username
