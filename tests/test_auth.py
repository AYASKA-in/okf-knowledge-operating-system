import pytest
from datetime import datetime, timezone

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password


class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = hash_password("test_password_123")
        assert verify_password("test_password_123", h)
        assert not verify_password("wrong_password", h)

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2
        assert verify_password("same_password", h1)
        assert verify_password("same_password", h2)

    def test_empty_password(self):
        h = hash_password("")
        assert verify_password("", h)
        assert not verify_password("not_empty", h)

    def test_unicode_password(self):
        pw = "pässwörd 🔐 日本語"
        h = hash_password(pw)
        assert verify_password(pw, h)

    def test_bcrypt_format(self):
        h = hash_password("test")
        assert h.startswith("$2b$") or h.startswith("$2a$") or h.startswith("$2y$")


class TestJWT:
    def test_create_access_token(self):
        token = create_access_token("user-1", "ws-1", "admin", {"dept": "eng"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_access_token(self):
        token = create_access_token("user-1", "ws-1", "editor")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-1"
        assert payload["ws"] == "ws-1"
        assert payload["role"] == "editor"
        assert payload["type"] == "access"
        assert "attrs" in payload
        assert "iat" in payload
        assert "exp" in payload
        assert "jti" in payload

    def test_access_token_with_attributes(self):
        attrs = {"department": "engineering", "location": "us-east"}
        token = create_access_token("u2", "ws2", "viewer", attrs)
        payload = decode_token(token)
        assert payload["attrs"]["department"] == "engineering"
        assert payload["attrs"]["location"] == "us-east"

    def test_access_token_no_attributes(self):
        token = create_access_token("u3", "ws3", "admin")
        payload = decode_token(token)
        assert payload["attrs"] == {}

    def test_create_and_decode_refresh_token(self):
        token = create_refresh_token("user-1")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"
        assert "jti" in payload

    def test_refresh_token_no_workspace_or_role(self):
        token = create_refresh_token("user-1")
        payload = decode_token(token)
        assert "ws" not in payload
        assert "role" not in payload

    def test_token_type_distinction(self):
        access = create_access_token("u1", "w1", "admin")
        refresh = create_refresh_token("u1")
        access_p = decode_token(access)
        refresh_p = decode_token(refresh)
        assert access_p["type"] == "access"
        assert refresh_p["type"] == "refresh"

    def test_token_contains_unique_jti(self):
        t1 = decode_token(create_access_token("u1", "w1", "admin"))
        t2 = decode_token(create_access_token("u1", "w1", "admin"))
        assert t1["jti"] != t2["jti"]

    def test_invalid_token_returns_none(self):
        assert decode_token("invalid.token.string") is None
        assert decode_token("") is None

    def test_tampered_token_returns_none(self):
        valid = create_access_token("u1", "w1", "admin")
        parts = valid.split(".")
        tampered = parts[0] + "." + parts[1] + ".invalidsignature"
        assert decode_token(tampered) is None
