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
from .models import BookedCourse, TodayCourse

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(
        key="load",
        name="Gym Load",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:account-group",
    ),
    SensorEntityDescription(
        key="total_participants",
        name="Total Course Participants",
        native_unit_of_measurement="people",
        icon="mdi:account-multiple",
    ),
    SensorEntityDescription(
        key="today_upcoming_courses",
        name="Today Upcoming Courses",
        icon="mdi:calendar-today",
    ),
    SensorEntityDescription(
        key="booked_courses",
        name="Booked Courses",
        icon="mdi:bookmark-check",
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
        CosmosSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)


class CosmosSensor(CoordinatorEntity, SensorEntity):
    """Base representation of a Cosmos sensor."""

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
    def native_value(self) -> int | str | None:
        """Return the native value of the sensor."""
        if self.coordinator.data is None:
            return None

        key = self.entity_description.key
        if key == "load":
            return self.coordinator.data.get("load", {}).get("percentage")
        if key == "total_participants":
            return sum(
                c.current_participants
                for c in self.coordinator.data.get("today_upcoming_courses", [])
            )
        if key == "today_upcoming_courses":
            courses = self.coordinator.data.get("today_upcoming_courses", [])
            return len(courses)
        if key == "booked_courses":
            return len(self.coordinator.data.get("booked_courses", []))
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return {}
        if self.entity_description.key == "today_upcoming_courses":
            courses: list[TodayCourse] = self.coordinator.data.get(
                "today_upcoming_courses", []
            )
            return {
                "courses": [
                    {
                        "course": c.course,
                        "participants": c.participants,
                        "current_participants": c.current_participants,
                        "percentage": c.percentage,
                        "start_time": c.start_time,
                        "end_time": c.end_time,
                    }
                    for c in courses
                ],
            }
        if self.entity_description.key == "booked_courses":
            booked: list[BookedCourse] = self.coordinator.data.get("booked_courses", [])
            return {
                "courses": [
                    {
                        "name": b.name,
                        "date": b.date,
                        "time": b.time,
                    }
                    for b in booked
                ],
            }
        return {}
