"""Sensor platform for Cosmos integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(
        key="load",
        name="Gym Load",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:account-group",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        CosmosLoadSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)


class CosmosLoadSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Cosmos load sensor."""

    def __init__(
        self,
        coordinator: Any,
        description: SensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Cosmos",
            "manufacturer": "Cosmos",
        }

    @property
    def native_value(self) -> int | None:
        """Return the native value of the sensor."""
        # Early exit: no data available (Law of Early Exit)
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("load", {}).get("percentage")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        # Early exit: no data available (Law of Early Exit)
        if self.coordinator.data is None:
            return None
        load_data = self.coordinator.data.get("load", {})
        return {
            "location": load_data.get("location"),
            "last_update_time": load_data.get("time"),
        }
