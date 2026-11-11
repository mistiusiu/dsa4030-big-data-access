import json
import logging
import time
from logging.handlers import WatchedFileHandler

from django.conf import settings

from .models import AuditLog

LOGIN_PATH = "/api/auth/token/"


def _siem_logger() -> logging.Logger:
    log = logging.getLogger("audit.siem")
    if not log.handlers:
        log.propagate = False
        log.setLevel(logging.INFO)
        try:
            settings.AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            log.addHandler(WatchedFileHandler(settings.AUDIT_LOG_FILE))
        except OSError:
            pass
        stdout = logging.StreamHandler()
        stdout.setFormatter(logging.Formatter("AUDIT %(message)s"))
        log.addHandler(stdout)
    return log


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _outcome(path: str, status: int) -> str:
    if path == LOGIN_PATH:
        if status == 200:
            return AuditLog.Outcome.LOGIN_SUCCESS
        if status == 429:
            return AuditLog.Outcome.THROTTLED
        return AuditLog.Outcome.LOGIN_FAILED
    if status < 400:
        return AuditLog.Outcome.ALLOWED
    if status == 401:
        return AuditLog.Outcome.UNAUTHENTICATED
    if status == 403:
        return AuditLog.Outcome.DENIED
    if status == 429:
        return AuditLog.Outcome.THROTTLED
    if status >= 500:
        return AuditLog.Outcome.ERROR
    return AuditLog.Outcome.REJECTED


class AuditMiddleware:
    """Records every /api/ request and its result. Passwords are never read."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.siem = _siem_logger()

    def __call__(self, request):
        if not request.path.startswith("/api/") or request.path == "/api/health/":
            return self.get_response(request)

        request.audit = {}
        attempted = None
        if request.path == LOGIN_PATH and request.method == "POST":
            try:
                attempted = str(json.loads(request.body or b"{}").get("username", ""))[:150]
            except (ValueError, AttributeError):
                attempted = None

        started = time.perf_counter()
        response = self.get_response(request)
        elapsed = (time.perf_counter() - started) * 1000

        user = getattr(request, "user", None)
        authed = bool(user and user.is_authenticated)
        token = getattr(request, "auth", None)
        detail = dict(request.audit)
        action = detail.pop("action", "")
        dataset = detail.pop("dataset", "")
        if request.GET:
            detail["query"] = {k: v for k, v in request.GET.items()}

        entry = AuditLog.objects.create(
            user=user if authed else None,
            username=user.username if authed else (attempted or ""),
            role=(user.role_id or "") if authed else "",
            method=request.method,
            path=request.path[:300],
            status_code=response.status_code,
            outcome=_outcome(request.path, response.status_code),
            action=action,
            dataset=dataset,
            ip=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
            duration_ms=round(elapsed, 2),
            token_jti=str(token.get("jti", "")) if token is not None and hasattr(token, "get") else "",
            detail=detail,
        )
        self.siem.info(json.dumps(entry.as_event(), default=str))
        response["X-Audit-Id"] = str(entry.pk)
        return response
