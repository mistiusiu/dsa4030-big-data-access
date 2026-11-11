from django.contrib import admin

from .models import Dataset, Policy


class PolicyInline(admin.TabularInline):
    model = Policy
    extra = 0
    fields = ["role", "mode", "cross_analyze", "min_group_size", "max_rows"]


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ["slug", "title", "domain"]
    inlines = [PolicyInline]


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ["role", "dataset", "mode", "cross_analyze", "min_group_size", "max_rows"]
    list_filter = ["role", "mode", "dataset__domain", "cross_analyze"]
    list_editable = ["mode", "cross_analyze", "min_group_size", "max_rows"]
    search_fields = ["role__name", "dataset__title", "rationale"]
    fieldsets = [
        (None, {"fields": ["role", "dataset", "mode", "rationale"]}),
        ("Record level", {"fields": ["column_rules", "cross_analyze", "max_rows"]}),
        ("Aggregates", {"fields": ["group_by", "metrics", "min_group_size"]}),
    ]
