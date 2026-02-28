"""Tests for crypto utility functions."""
from app.services.crypto import encrypt_api_key, decrypt_api_key, mask_api_key


class TestMaskApiKey:
    def test_masks_long_key(self):
        result = mask_api_key("sk-ant-api03-abcdefghijklmnop")
        assert result.startswith("sk-ant-api03")
        assert result.endswith("***")

    def test_masks_short_key(self):
        result = mask_api_key("short")
        assert result == "***"

    def test_empty_key(self):
        result = mask_api_key("")
        assert result == ""


class TestEncryptDecrypt:
    def test_roundtrip(self):
        original = "sk-test-key-12345"
        encrypted = encrypt_api_key(original)
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == original

    def test_encrypted_differs_from_original(self):
        original = "sk-test-key-12345"
        encrypted = encrypt_api_key(original)
        assert decrypt_api_key(encrypted) == original
