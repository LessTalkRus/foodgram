from django.core.management.base import BaseCommand

from recipes.models import User


class Command(BaseCommand):
    help = "backfill the data"

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Почта пользователя")

    def handle(self, *args, **kwargs):
        email = kwargs["email"]
        try:
            user = User.objects.get(email=email)
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Пользователь {email} теперь является суперюзером,"
                    f" имеет права staff и активен."
                )
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Пользователь {email} не найден!")
            )
