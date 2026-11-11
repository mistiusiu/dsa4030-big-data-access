from datetime import UTC, datetime

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Role, User


def expiry(token) -> str:
    return datetime.fromtimestamp(token["exp"], tz=UTC).isoformat()


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role_id
        token["role_name"] = user.role.name if user.role else None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.role_id:
            raise serializers.ValidationError(
                {"detail": "This account has no role on the permission grid."}
            )
        refresh = RefreshToken(data["refresh"])
        data["access_expires"] = expiry(refresh.access_token)
        data["refresh_expires"] = expiry(refresh)
        data["role"] = self.user.role_id
        return data


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["slug", "name", "description", "icon", "capabilities"]


class MeSerializer(serializers.ModelSerializer):
    role = RoleSerializer()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role", "last_login"]
