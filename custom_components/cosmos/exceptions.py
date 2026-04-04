"""Custom exceptions for Cosmos"""


class CosmosError(Exception):
    """Base exception for Cosmos"""


class AuthenticationError(CosmosError):
    """Login failed"""


class BookingError(CosmosError):
    """Booking failed"""


class ConfigurationError(CosmosError):
    """Missing or invalid config"""
