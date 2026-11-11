import base64

from cryptography.hazmat.primitives.serialization import load_pem_public_key
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Role, User
from .serializers import MeSerializer, RoleSerializer, expiry


class LoginView(TokenObtainPairView):
    """Exchange username + password for an RS256 access/refresh pair."""

    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class RefreshView(TokenRefreshView):
    """Rotate a refresh token. The old refresh token is blacklisted."""

    authentication_classes = []

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data["access_expires"] = expiry(AccessToken(response.data["access"]))
            if "refresh" in response.data:
                response.data["refresh_expires"] = expiry(RefreshToken(response.data["refresh"]))
        return response


class LogoutView(APIView):
    """Blacklist the supplied refresh token so it can never be rotated again."""

    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh", "")).blacklist()
        except TokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Refresh token revoked."})


class MeView(APIView):
    def get(self, request):
        data = MeSerializer(request.user).data
        data["token_claims"] = dict(request.auth.payload) if request.auth else {}
        return Response(data)


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class JWKSView(APIView):
    """Public verification key, as PEM and as a JWK. Safe to publish."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        numbers = load_pem_public_key(settings.JWT_PUBLIC_KEY.encode()).public_numbers()
        return Response(
            {
                "algorithm": settings.SIMPLE_JWT["ALGORITHM"],
                "issuer": settings.SIMPLE_JWT["ISSUER"],
                "audience": settings.SIMPLE_JWT["AUDIENCE"],
                "public_key_pem": settings.JWT_PUBLIC_KEY,
                "keys": [
                    {
                        "kty": "RSA",
                        "use": "sig",
                        "alg": "RS256",
                        "n": _b64url_uint(numbers.n),
                        "e": _b64url_uint(numbers.e),
                    }
                ],
            }
        )


class DemoAccountsView(APIView):
    """Lab-only: the seeded account for each role, so the login page can offer a
    role picker. Disable with EXPOSE_DEMO_ACCOUNTS=false."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.EXPOSE_DEMO_ACCOUNTS:
            return Response({"accounts": [], "password_hint": None})
        accounts = []
        for role in Role.objects.all():
            user = User.objects.filter(role=role, is_active=True).order_by("id").first()
            if user:
                accounts.append({"username": user.username, "role": RoleSerializer(role).data})
        return Response({"accounts": accounts, "password": settings.DEMO_PASSWORD})
