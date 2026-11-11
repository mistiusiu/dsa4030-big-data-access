"""RSA key material for signing JWTs (RS256).

The private key signs tokens; the public key verifies them and is published at
/api/auth/jwks/. Keys live on a Docker volume so tokens survive restarts. If the
files are missing (first boot, or the test suite) a fresh pair is generated.
"""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def load_or_create_keypair(key_dir: Path) -> tuple[str, str]:
    private_path = key_dir / "jwt_private.pem"
    public_path = key_dir / "jwt_public.pem"
    if private_path.exists() and public_path.exists():
        return private_path.read_text(), public_path.read_text()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    try:
        key_dir.mkdir(parents=True, exist_ok=True)
        private_path.write_text(private_pem)
        private_path.chmod(0o600)
        public_path.write_text(public_pem)
    except OSError:
        # Read-only filesystem: keep the pair in memory for this process only.
        pass
    return private_pem, public_pem
