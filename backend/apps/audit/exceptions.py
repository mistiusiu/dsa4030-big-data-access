from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken

from .context import note


def _token_reason(exc: InvalidToken) -> str:
    text = str(exc.detail).lower()
    if "expired" in text:
        return "token_expired"
    if "blacklisted" in text:
        return "token_blacklisted"
    return "token_invalid"  # bad signature, alg: none, malformed


def audited_exception_handler(exc, context):
    """DRF's handler, plus a machine-readable failure reason for the audit log."""
    response = exception_handler(exc, context)
    request = context.get("request")
    if request is not None and response is not None:
        if isinstance(exc, InvalidToken):
            reason = _token_reason(exc)
        else:
            codes = exc.get_codes() if hasattr(exc, "get_codes") else None
            reason = codes if isinstance(codes, str) else getattr(exc, "default_code", type(exc).__name__)
        note(request, reason=reason, message=str(getattr(exc, "detail", exc))[:300])
    return response
