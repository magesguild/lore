"""Ed25519 signing and verification for Lore manifests."""

from __future__ import annotations

from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


class SignatureError(ValueError):
    """A Lore signature could not be loaded or verified."""


def sign_manifest(manifest: Path, private_key: Path, signature: Path) -> None:
    try:
        key = serialization.load_pem_private_key(private_key.read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as exc:
        raise SignatureError(f"could not load Ed25519 private key: {exc}") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise SignatureError("signing key is not an Ed25519 private key")
    signature.write_bytes(key.sign(manifest.read_bytes()))


def verify_manifest(manifest: Path, signature: Path, public_key: Path) -> None:
    try:
        key = serialization.load_pem_public_key(public_key.read_bytes())
    except (OSError, ValueError, TypeError) as exc:
        raise SignatureError(f"could not load Ed25519 public key: {exc}") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise SignatureError("publisher key is not an Ed25519 public key")
    try:
        key.verify(signature.read_bytes(), manifest.read_bytes())
    except (OSError, InvalidSignature) as exc:
        raise SignatureError("manifest signature is invalid") from exc
