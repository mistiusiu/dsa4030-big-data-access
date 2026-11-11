from rest_framework.permissions import BasePermission


def require(capability: str) -> type[BasePermission]:
    """Permission class demanding an API capability from the caller's role."""

    class HasCapability(BasePermission):
        message = f"Your role lacks the '{capability}' capability."

        def has_permission(self, request, view):
            return bool(request.user and request.user.is_authenticated and request.user.can(capability))

    HasCapability.__name__ = f"Requires_{capability.replace('.', '_')}"
    return HasCapability
