import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredient, Tag


class Command(BaseCommand):
    help = "backfill the data"

    def add_arguments(self, parser):
        parser.add_argument(
            "filename", type=str, help="filename which contains JSON-array"
        )

    def handle(self, *args, **kwargs):
        Tag.objects.get_or_create(name="General", slug="general")

        file_path = kwargs["filename"]
        self.stdout.write(self.style.SUCCESS(f"{file_path}"))

        # Открываем файл
        with open(file_path) as f:
            for r in json.loads(f.read()):
                _, created = Ingredient.objects.get_or_create(
                    name=r["name"], measurement_unit=r["measurement_unit"]
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Записан: {r["name"]}'))
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'already exists: {r["name"]}')
                    )
