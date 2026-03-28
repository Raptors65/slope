import hashlib
import hmac

from app.services.github_signature import verify_github_webhook_signature


def test_valid_hex_signature() -> None:
    secret = "my-secret"
    body = b'{"hello":"world"}'
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    header = f"sha256={digest}"
    assert verify_github_webhook_signature(body, header, secret) is True


def test_wrong_secret() -> None:
    body = b"{}"
    digest = hmac.new(b"right", body, hashlib.sha256).hexdigest()
    assert verify_github_webhook_signature(body, f"sha256={digest}", "wrong") is False


def test_missing_prefix() -> None:
    assert verify_github_webhook_signature(b"{}", "deadbeef", "secret") is False
