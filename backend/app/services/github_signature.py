import hashlib
import hmac


def verify_github_webhook_signature(
    body: bytes,
    signature_header: str | None,
    secret: str,
) -> bool:
    """Validate X-Hub-Signature-256: sha256=<hex> over raw body (GitHub webhook secret)."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected_hex = signature_header[7:]
    try:
        expected = bytes.fromhex(expected_hex)
    except ValueError:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return hmac.compare_digest(digest, expected)
