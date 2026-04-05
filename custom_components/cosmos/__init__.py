"""The Cosmos integration."""

from __future__ import annotations

import datetime
import logging
from typing import Any

import voluptuous as vol

# Home Assistant imports - only available when running inside HA
# These are optional to allow standalone CLI usage
try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import (
        HomeAssistant,
        ServiceCall,
        ServiceResponse,
        SupportsResponse,
    )
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.helpers import config_validation as cv
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False  # type: ignore[misc,assignment]
    ConfigEntry = None  # type: ignore[misc,assignment]
    HomeAssistant = None  # type: ignore[misc,assignment]
    ServiceCall = None  # type: ignore[misc,assignment]
    ServiceResponse = None  # type: ignore[misc,assignment]
    HomeAssistantError = Exception  # type: ignore[misc,assignment]
    cv = None  # type: ignore[misc,assignment]
    DataUpdateCoordinator = None  # type: ignore[misc,assignment]

from .api_client import CosmosClient
from .booking import BookingOptions, book_course
from .config import load_config_from_dict
from .const import (
    CONF_PASSWORD as CONF_PASSWORD,
)
from .const import (
    CONF_USERNAME as CONF_USERNAME,
)
from .const import (
    DOMAIN,
    SERVICE_BOOK,
)
from .exceptions import CosmosError
from .utils import parse_weekday

_LOGGER = logging.getLogger(__name__)

# Service schema - only defined when running inside HA
if HA_AVAILABLE and cv is not None:
    SERVICE_SCHEMA = vol.Schema(
        {
            vol.Required("course"): cv.string,
            vol.Required("day"): vol.Any(
                vol.All(vol.Coerce(int), vol.Range(min=1, max=7)),
                cv.string,
            ),
            vol.Required("time"): cv.string,
        }
    )
else:
    SERVICE_SCHEMA = None  # type: ignore[misc,assignment]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Cosmos integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cosmos from a config entry."""

    # Parse config at boundary (Law of Parse Don't Validate)
    try:
        config = load_config_from_dict(entry.data)
    except CosmosError as err:
        _LOGGER.error("Invalid configuration: %s", err)
        return False

    # Get update interval from options (default 5 minutes)
    update_interval = datetime.timedelta(
        minutes=entry.options.get("update_interval", 5)
    )

    # Create coordinator for data updates
    async def async_update_data() -> dict[str, Any]:
        """Fetch data from API."""
        now = datetime.datetime.now()
        hour = now.hour

        # Studio closed between 22:00 and 07:00 - return 0 load
        if hour < 7 or hour >= 22:
            _LOGGER.debug("Studio closed (hour=%s), returning 0 load", hour)
            return {"load": {"percentage": 0}}

        # Studio open - fetch actual load
        async with CosmosClient(config) as client:
            await client.login()
            load_data = await client.get_load()
            return {"load": {"percentage": load_data.get("percentage", 0)}}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="cosmos_load",
        update_method=async_update_data,
        update_interval=update_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator for sensor platform
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    # Setup sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    async def handle_book(call: ServiceCall) -> ServiceResponse:
        """Handle the cosmos.book service call."""
        course = call.data["course"]
        day_value = call.data["day"]
        time = call.data["time"]

        # Parse day value - accept both string (Mon/Tue) and int (1-7)
        # (Law of Parse Don't Validate - parse at boundary)
        if isinstance(day_value, str):
            try:
                day = parse_weekday(day_value)
            except ValueError as e:
                raise HomeAssistantError(str(e)) from None
        else:
            day = day_value

        # Early exit: validate time format (Law of Early Exit)
        try:
            hours, minutes = map(int, time.split(":"))
        except ValueError:
            raise HomeAssistantError(
                f"Invalid time format: {time}. Use HH:MM format."
            ) from None

        # Validate hours and minutes range
        if hours < 0 or hours > 23:
            raise HomeAssistantError(f"Invalid hours: {hours}. Must be 0-23.")
        if minutes < 0 or minutes > 59:
            raise HomeAssistantError(f"Invalid minutes: {minutes}. Must be 0-59.")

        try:
            async with CosmosClient(config) as client:
                await client.login()

                options = BookingOptions(
                    course=course,
                    day=day,
                    hours=hours,
                    minutes=minutes,
                )

                result = await book_course(client, options)

                # Log booking result with full details
                day_name = datetime.date(2024, 1, day).strftime(
                    "%A"
                )  # Convert day number to name
                time_str = f"{hours:02d}:{minutes:02d}"
                message = result.get("message", "")

                if "already booked" in message.lower():
                    _LOGGER.info(
                        "Booking already done: %s on %s at %s - %s",
                        course,
                        day_name,
                        time_str,
                        message,
                    )
                else:
                    _LOGGER.info(
                        "Booking successful: %s on %s at %s - %s",
                        course,
                        day_name,
                        time_str,
                        message,
                    )

                return result

        except CosmosError as err:
            day_name = datetime.date(2024, 1, day).strftime("%A")
            time_str = f"{hours:02d}:{minutes:02d}"
            _LOGGER.error(
                "Booking failed: %s on %s at %s - %s", course, day_name, time_str, err
            )
            raise HomeAssistantError(f"Booking failed: {err}") from err

    # Register service
    hass.services.async_register(
        DOMAIN,
        SERVICE_BOOK,
        handle_book,
        schema=SERVICE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    _LOGGER.info("Cosmos integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload sensor platform
    await hass.config_entries.async_unload_platforms(entry, ["sensor"])

    # Remove service
    hass.services.async_remove(DOMAIN, SERVICE_BOOK)

    # Clean up stored data
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    _LOGGER.info("Cosmos integration unloaded")
    return True
