from django.core.exceptions import ValidationError
from django.db import models

from apps.lake.catalog import BY_SLUG

TRANSFORMS = {
    "clear": "Shown as stored",
    "mask": "Partially hidden (e.g. last 4 digits, initial only)",
    "pseudonym": "Replaced by a keyed hash, stable within this role so joins still work",
    "fake": "Replaced by a pseudorandom but realistic stand-in (e.g. fake name)",
    "generalize": "Coarsened (age band, month, ~1 km grid, street only)",
    "redact": "Column removed entirely",
}


class Dataset(models.Model):
    slug = models.SlugField(primary_key=True, max_length=40)
    title = models.CharField(max_length=80)
    domain = models.CharField(max_length=80)
    icon = models.CharField(max_length=40, default="database")
    description = models.TextField()

    class Meta:
        ordering = ["domain", "title"]

    def __str__(self) -> str:
        return self.title


class Policy(models.Model):
    class Mode(models.TextChoices):
        DENY = "deny", "Deny"
        AGGREGATE = "aggregate", "Aggregate only"
        ROW = "row", "Record level"

    role = models.ForeignKey("accounts.Role", on_delete=models.CASCADE, related_name="policies")
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="policies")
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.DENY)
    column_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="{column: clear|mask|pseudonym|fake|generalize|redact}. Unlisted columns are redacted.",
    )
    group_by = models.JSONField(default=list, blank=True, help_text="Allowed dimensions. Empty = all.")
    metrics = models.JSONField(default=list, blank=True, help_text="Allowed measures. Empty = all.")
    min_group_size = models.PositiveIntegerField(default=1, help_text="k-anonymity: smaller groups are suppressed")
    cross_analyze = models.BooleanField(default=False, help_text="Expose to the SQL workbench for joins")
    max_rows = models.PositiveIntegerField(default=200)
    rationale = models.TextField(blank=True)

    class Meta:
        unique_together = [("role", "dataset")]
        ordering = ["role__ordering", "dataset__domain"]
        verbose_name_plural = "policies"

    def __str__(self) -> str:
        return f"{self.role_id} → {self.dataset_id}: {self.mode}"

    def clean(self):
        ds = BY_SLUG.get(self.dataset_id)
        if not ds:
            raise ValidationError({"dataset": "Dataset is not in the lake catalog."})
        names = {c.name for c in ds.columns}
        bad_cols = set(self.column_rules) - names
        bad_rules = {v for v in self.column_rules.values() if v not in TRANSFORMS}
        if bad_cols:
            raise ValidationError({"column_rules": f"Unknown columns: {sorted(bad_cols)}"})
        if bad_rules:
            raise ValidationError({"column_rules": f"Unknown transforms: {sorted(bad_rules)}"})
        if set(self.group_by) - set(ds.dimensions):
            raise ValidationError({"group_by": f"Valid dimensions: {sorted(ds.dimensions)}"})
        if set(self.metrics) - set(ds.measures):
            raise ValidationError({"metrics": f"Valid measures: {sorted(ds.measures)}"})
