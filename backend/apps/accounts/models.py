from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    slug = models.SlugField(primary_key=True, max_length=40)
    name = models.CharField(max_length=80)
    description = models.TextField()
    icon = models.CharField(max_length=40, default="user", help_text="lucide-react icon name")
    capabilities = models.JSONField(default=list, blank=True)
    ordering = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["ordering", "name"]

    def __str__(self) -> str:
        return self.name

    def can(self, capability: str) -> bool:
        return capability in self.capabilities


class User(AbstractUser):
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.PROTECT, related_name="users")

    def can(self, capability: str) -> bool:
        return bool(self.role and self.role.can(capability))
