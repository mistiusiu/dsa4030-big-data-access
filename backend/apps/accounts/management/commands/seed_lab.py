import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Role, User
from apps.grid.models import Dataset, Policy
from apps.grid.seed import GRID, ROLES
from apps.lake.catalog import DATASETS


class Command(BaseCommand):
    help = "Seed roles, datasets, the permission grid, demo users and the super-admin."

    def add_arguments(self, parser):
        parser.add_argument("--reset-grid", action="store_true",
                            help="Overwrite policies a super-admin may have edited")

    @transaction.atomic
    def handle(self, *args, reset_grid, **opts):
        for i, r in enumerate(ROLES):
            Role.objects.update_or_create(slug=r["slug"], defaults={
                "name": r["name"], "description": r["description"], "icon": r["icon"],
                "capabilities": r["capabilities"], "ordering": i,
            })
        for ds in DATASETS:
            Dataset.objects.update_or_create(slug=ds.slug, defaults={
                "title": ds.title, "domain": ds.domain, "icon": ds.icon, "description": ds.description,
            })

        created = updated = 0
        for role, cells in GRID.items():
            for slug, cell in cells.items():
                defaults = {"column_rules": {}, "group_by": [], "metrics": [], "min_group_size": 1,
                            "cross_analyze": False, "max_rows": 200, **cell}
                if reset_grid:
                    _, was_created = Policy.objects.update_or_create(role_id=role, dataset_id=slug, defaults=defaults)
                else:
                    _, was_created = Policy.objects.get_or_create(role_id=role, dataset_id=slug, defaults=defaults)
                if was_created:
                    created += 1
                elif reset_grid:
                    updated += 1
        self.stdout.write(f"Grid: {created} policies created, {updated} reset.")

        for r in ROLES:
            user, made = User.objects.get_or_create(username=r["username"], defaults={
                "first_name": r["first_name"], "last_name": r["last_name"], "role_id": r["slug"],
                "email": f"{r['username']}@mjimpya.city",
            })
            if made:
                user.set_password(settings.DEMO_PASSWORD)
                user.save()
                self.stdout.write(f"  demo user {r['username']:<14} → {r['name']}")

        su_name = os.environ.get("DJANGO_SUPERUSER_USERNAME", "superadmin")
        su_pass = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if su_pass and not User.objects.filter(username=su_name).exists():
            # The super-admin manages the grid in Django admin. It has no role, so
            # it cannot obtain an API token or read the lake itself.
            User.objects.create_superuser(su_name, os.environ.get("DJANGO_SUPERUSER_EMAIL", ""), su_pass)
            self.stdout.write(f"  super-admin {su_name} created")
        self.stdout.write(self.style.SUCCESS("Lab seeded."))
