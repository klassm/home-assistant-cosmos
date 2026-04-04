"""Configuration loading utilities"""

from .exceptions import ConfigurationError
from .models import Config


def load_config_from_env() -> Config:
    """Load configuration from environment variables (.env file).

    Used by CLI entry point.
    """
    import os

    from dotenv import load_dotenv

    load_dotenv()

    username = os.getenv("COSMOS_USERNAME")
    password = os.getenv("COSMOS_PASSWORD")
    mandant = os.getenv("COSMOS_MANDANT")

    if not username or not password or not mandant:
        raise ConfigurationError(
            "Missing COSMOS_USERNAME, COSMOS_PASSWORD, or COSMOS_MANDANT in .env"
        )

    return Config(username=username, password=password, mandant=mandant)


def load_config_from_dict(data: dict) -> Config:
    """Load configuration from a dictionary.

    Used by Home Assistant integration.
    """
    try:
        return Config(
            username=data["username"],
            password=data["password"],
            mandant=data["mandant"],
        )
    except KeyError as e:
        raise ConfigurationError(f"Missing config key: {e}") from e
