from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "username", "role", "method", "path", "status_code", "outcome", "dataset", "ip"]
    list_filter = ["outcome", "role", "method", "dataset"]
    search_fields = ["username", "path", "ip", "token_jti"]
    date_hierarchy = "timestamp"

    # The audit trail is append-only, even for the super-admin.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
