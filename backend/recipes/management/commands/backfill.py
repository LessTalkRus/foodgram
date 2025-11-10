import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredient, Tag


class Command(BaseCommand):
    help = "backfill the data"

    def add_arguments(self, parser):
        parser.add_argument(
            "filename", type=str, help="JSON-файл с ингредиентами"
        )

    def handle(self, *args, **kwargs):
        # --- Создание базовых тегов ---
        tags_data = [
            # 🍽️ Основные категории
            ("Завтрак", "breakfast"),
            ("Обед", "lunch"),
            ("Ужин", "dinner"),
            ("Закуски", "snacks"),
            # ("Супы",  "soups"),
            # ("Десерты", "desserts"),
            # ("Выпечка", "baking"),
            # ("Пицца", "pizza"),
            # ("Салаты", "salads"),
            # ("Напитки", "drinks"),
            # ("Маринад", "marinade"),
            # 🌍 Национальные кухни
            # ("Итальянская кухня", "italian"),
            # ("Грузинская кухня", "georgian"),
            # ("Кавказская кухня", "caucasian"),
            # ("Азиатская кухня", "asian"),
            # ("Японская кухня (суши, роллы)", "japanese"),
            # ("Мексиканская кухня", "mexican"),
            # ("Американская кухня", "american"),
            # ("Французская кухня", "french"),
            # ("Средиземноморская кухня", "mediterranean"),
            # 🌱 Диетические и особые
            # ("Вегетарианская кухня", "vegetarian"),
            # ("Веганская кухня", "vegan"),
            # ("Безглютеновые блюда", "gluten-free"),
            # ("Кето", "keto"),
            # ("Фитнес-кухня", "fitness"),
            # ("Детское питание", "kids"),
            # ("Экзотика", "exotic"),
        ]

        for name, slug in tags_data:
            tag, created = Tag.objects.get_or_create(name=name, slug=slug)
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Создан тег: {name}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Тег уже существует: {name}")
                )

        # --- Загрузка ингредиентов ---
        file_path = kwargs["filename"]
        self.stdout.write(self.style.SUCCESS(f"{file_path}"))

        with open(file_path) as f:
            for r in json.loads(f.read()):
                _, created = Ingredient.objects.get_or_create(
                    name=r["name"], measurement_unit=r["measurement_unit"]
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Записан ингредиент: {r["name"]}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'⚠️ Ингредиент уже существует: {r["name"]}'
                        )
                    )
