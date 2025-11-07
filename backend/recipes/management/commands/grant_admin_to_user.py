from django.core.management.base import BaseCommand

from recipes.models import User


class Command(BaseCommand):
    help = "backfill the data"

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="user email for update")

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
                    f"User {email} is now an admin, "
                    f"an staff and forced activated."
                )
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"User with email {email} not found.")
            )
