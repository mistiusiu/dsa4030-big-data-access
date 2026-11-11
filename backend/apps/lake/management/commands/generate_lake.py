from django.conf import settings
from django.core.management.base import BaseCommand

from apps.lake.catalog import DATASETS
from apps.lake.generator import generate


class Command(BaseCommand):
    help = "Generate the synthetic Parquet data lake (skips if it already exists)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Regenerate even if files exist")
        parser.add_argument("--scale", type=float, default=settings.LAKE_SCALE)
        parser.add_argument("--seed", type=int, default=settings.LAKE_SEED)

    def handle(self, *args, force, scale, seed, **opts):
        lake = settings.LAKE_DIR
        if not force and all((lake / ds.filename).exists() for ds in DATASETS):
            self.stdout.write(f"Lake already present in {lake} — skipping (use --force to rebuild).")
            return
        self.stdout.write(f"Generating lake in {lake} (seed={seed}, scale={scale})…")
        for slug, n in generate(lake, seed=seed, scale=scale).items():
            self.stdout.write(f"  {slug:<18} {n:>8,} rows")
        self.stdout.write(self.style.SUCCESS("Data lake ready."))
