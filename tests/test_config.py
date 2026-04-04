"""Tests for configuration loading"""

from unittest.mock import patch

import pytest

# Import directly from submodules to avoid HA dependencies in __init__.py
from custom_components.cosmos.config import (
    load_config_from_dict,
    load_config_from_env,
)
from custom_components.cosmos.exceptions import ConfigurationError


def test_load_config_from_dict():
    """Test loading config from dict"""
    data = {"username": "user123", "password": "pass456", "mandant": "test_mandant"}
    config = load_config_from_dict(data)

    assert config.username == "user123"
    assert config.password == "pass456"
    assert config.mandant == "test_mandant"


def test_load_config_from_dict_with_mandant():
    """Test loading config from dict with custom mandant"""
    data = {"username": "user123", "password": "pass456", "mandant": "custom_mandant"}
    config = load_config_from_dict(data)

    assert config.username == "user123"
    assert config.password == "pass456"
    assert config.mandant == "custom_mandant"


def test_load_config_from_dict_missing_username():
    """Test config loading with missing username"""
    data = {"password": "pass456", "mandant": "test_mandant"}

    with pytest.raises(ConfigurationError, match="Missing config key"):
        load_config_from_dict(data)


def test_load_config_from_dict_missing_password():
    """Test config loading with missing password"""
    data = {"username": "user123", "mandant": "test_mandant"}

    with pytest.raises(ConfigurationError, match="Missing config key"):
        load_config_from_dict(data)


def test_load_config_from_dict_missing_mandant():
    """Test config loading with missing mandant"""
    data = {"username": "user123", "password": "pass456"}

    with pytest.raises(ConfigurationError, match="Missing config key"):
        load_config_from_dict(data)


def test_load_config_from_dict_empty():
    """Test config loading with empty dict"""
    data = {}

    with pytest.raises(ConfigurationError, match="Missing config key"):
        load_config_from_dict(data)


def test_load_config_from_env(monkeypatch):
    """Test loading config from environment"""
    monkeypatch.setenv("COSMOS_USERNAME", "env_user")
    monkeypatch.setenv("COSMOS_PASSWORD", "env_pass")
    monkeypatch.setenv("COSMOS_MANDANT", "env_mandant")

    config = load_config_from_env()

    assert config.username == "env_user"
    assert config.password == "env_pass"
    assert config.mandant == "env_mandant"


def test_load_config_from_env_with_mandant(monkeypatch):
    """Test loading config from environment with custom mandant"""
    monkeypatch.setenv("COSMOS_USERNAME", "env_user")
    monkeypatch.setenv("COSMOS_PASSWORD", "env_pass")
    monkeypatch.setenv("COSMOS_MANDANT", "custom_mandant")

    config = load_config_from_env()

    assert config.username == "env_user"
    assert config.password == "env_pass"
    assert config.mandant == "custom_mandant"


def test_load_config_from_env_missing_username(monkeypatch):
    """Test config loading with missing username env var"""
    monkeypatch.delenv("COSMOS_USERNAME", raising=False)
    monkeypatch.delenv("COSMOS_PASSWORD", raising=False)
    monkeypatch.delenv("COSMOS_MANDANT", raising=False)

    with patch("dotenv.load_dotenv"):
        with pytest.raises(
            ConfigurationError,
            match="Missing COSMOS_USERNAME, COSMOS_PASSWORD, or COSMOS_MANDANT",
        ):
            load_config_from_env()


def test_load_config_from_env_missing_password(monkeypatch):
    """Test config loading with missing password env var"""
    monkeypatch.setenv("COSMOS_USERNAME", "env_user")
    monkeypatch.delenv("COSMOS_PASSWORD", raising=False)
    monkeypatch.delenv("COSMOS_MANDANT", raising=False)

    with patch("dotenv.load_dotenv"):
        with pytest.raises(
            ConfigurationError,
            match="Missing COSMOS_USERNAME, COSMOS_PASSWORD, or COSMOS_MANDANT",
        ):
            load_config_from_env()


def test_load_config_from_env_missing_mandant(monkeypatch):
    """Test config loading with missing mandant env var"""
    monkeypatch.setenv("COSMOS_USERNAME", "env_user")
    monkeypatch.setenv("COSMOS_PASSWORD", "env_pass")
    monkeypatch.delenv("COSMOS_MANDANT", raising=False)

    with patch("dotenv.load_dotenv"):
        with pytest.raises(
            ConfigurationError,
            match="Missing COSMOS_USERNAME, COSMOS_PASSWORD, or COSMOS_MANDANT",
        ):
            load_config_from_env()


def test_load_config_from_env_both_missing(monkeypatch):
    """Test config loading with both env vars missing"""
    monkeypatch.delenv("COSMOS_USERNAME", raising=False)
    monkeypatch.delenv("COSMOS_PASSWORD", raising=False)
    monkeypatch.delenv("COSMOS_MANDANT", raising=False)

    with patch("dotenv.load_dotenv"):
        with pytest.raises(ConfigurationError):
            load_config_from_env()
