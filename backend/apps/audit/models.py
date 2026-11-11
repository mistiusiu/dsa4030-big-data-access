from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Outcome(models.TextChoices):
        ALLOWED = "allowed"
        DENIED = "denied"
        UNAUTHENTICATED = "unauthenticated"
        LOGIN_SUCCESS = "login_success"
        LOGIN_FAILED = "login_failed"
        REJECTED = "rejected"
        THROTTLED = "throttled"
        ERROR = "error"

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=150, blank=True, db_index=True)
    role = models.CharField(max_length=40, blank=True, db_index=True)
    method = models.CharField(max_length=8)
    path = models.CharField(max_length=300)
    status_code = models.PositiveSmallIntegerField()
    outcome = models.CharField(max_length=20, choices=Outcome.choices, db_index=True)
    action = models.CharField(max_length=60, blank=True)
    dataset = models.CharField(max_length=40, blank=True, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    duration_ms = models.FloatField(default=0)
    token_jti = models.CharField(max_length=64, blank=True)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.timestamp:%H:%M:%S} {self.username or '-'} {self.method} {self.path} {self.outcome}"

    def as_event(self) -> dict:
        """Flat, ECS-flavoured record for SIEM ingestion."""
        return {
            "@timestamp": self.timestamp.isoformat(),
            "event.id": self.pk,
            "event.action": self.action or f"{self.method} {self.path}",
            "event.outcome": self.outcome,
            "http.request.method": self.method,
            "url.path": self.path,
            "http.response.status_code": self.status_code,
            "user.name": self.username or None,
            "user.roles": [self.role] if self.role else [],
            "source.ip": self.ip,
            "user_agent.original": self.user_agent,
            "event.duration_ms": self.duration_ms,
            "jwt.jti": self.token_jti or None,
            "lab.dataset": self.dataset or None,
            "lab.detail": self.detail,
        }
