from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "ordering"]
    list_editable = ["ordering"]


@admin.register(User)
class LabUserAdmin(UserAdmin):
    list_display = ["username", "first_name", "last_name", "role", "is_active", "is_superuser", "last_login"]
    list_filter = ["role", "is_active", "is_superuser"]
    fieldsets = UserAdmin.fieldsets + (("Permission grid", {"fields": ["role"]}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Permission grid", {"fields": ["role"]}),)
