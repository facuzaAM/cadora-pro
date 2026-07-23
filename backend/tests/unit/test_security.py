"""Tests for the security utils (password hashing)."""

import pytest

from app.utils.security import hash_password, verify_password


def test_hash_and_verify():
    password = "test-password-123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


def test_different_hashes():
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    assert h1 != h2
    assert verify_password("same-password", h1) is True
    assert verify_password("same-password", h2) is True


def test_password_validation():
    from pydantic import ValidationError

    from app.schemas.auth import RegisterRequest

    # Too short
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.com", password="Ab1!", name="Test")

    # No uppercase
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.com", password="test123!@", name="Test")

    # No number
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.com", password="TestTest!@", name="Test")

    # No special char
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.com", password="TestTest12", name="Test")

    # Valid password
    req = RegisterRequest(email="a@b.com", password="TestTest12!@", name="Test")
    assert req.password == "TestTest12!@"
