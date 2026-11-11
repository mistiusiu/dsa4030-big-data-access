from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class RoleBoundJWTAuthentication(JWTAuthentication):
    """JWT auth that also binds the token to the user's *current* role.

    The signature already stops a client from editing the ``role`` claim. This
    check covers the other direction: if a super-admin moves a user to another
    role, tokens minted under the old role stop working immediately instead of
    living on until they expire.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if validated_token.get("role") != user.role_id:
            raise AuthenticationFailed(
                "Token role claim does not match the account's current role.",
                code="role_mismatch",
            )
        return user
