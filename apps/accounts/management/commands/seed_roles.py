from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

ROLES = ["sales", "production", "accounting"]


class Command(BaseCommand):
    help = "Create the standard role groups (sales, production, accounting) if they don't exist."

    def handle(self, *args, **options):
        for role in ROLES:
            group, created = Group.objects.get_or_create(name=role)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created group '{role}'"))
            else:
                self.stdout.write(f"Group '{role}' already exists")
