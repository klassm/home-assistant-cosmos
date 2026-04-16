"""Utility functions for Cosmos integration."""

from __future__ import annotations

from datetime import datetime

from .models import TodayCourse


def parse_weekday(day_input: str) -> int:
    """Parse weekday from number or name.

    Args:
        day_input: Day as number (1-7), German short name (Mo-So),
            or English short name (Mon-Sun)

    Returns:
        Day number (1=Monday, 7=Sunday)

    Raises:
        ValueError: If input is not a valid weekday
    """
    # Early exit: normalize input (Law of Early Exit)
    day_normalized = day_input.strip().lower()

    # Try parsing as number
    try:
        day_num = int(day_normalized)
        if 1 <= day_num <= 7:
            return day_num
    except ValueError:
        pass

    # Mapping for weekday names
    weekday_map = {
        # German short names
        "mo": 1,
        "di": 2,
        "mi": 3,
        "do": 4,
        "fr": 5,
        "sa": 6,
        "so": 7,
        # English short names
        "mon": 1,
        "tue": 2,
        "wed": 3,
        "thu": 4,
        "fri": 5,
        "sat": 6,
        "sun": 7,
        # English full names (bonus)
        "monday": 1,
        "tuesday": 2,
        "wednesday": 3,
        "thursday": 4,
        "friday": 5,
        "saturday": 6,
        "sunday": 7,
    }

    # Fail fast: invalid weekday (Law of Fail Fast)
    if day_normalized in weekday_map:
        return weekday_map[day_normalized]

    raise ValueError(
        f"Invalid weekday: {day_input}. Use 1-7, Mo-So (German), or Mon-Sun (English)."
    )


def filter_upcoming_courses(
    courses: list[TodayCourse], now: datetime | None = None
) -> list[TodayCourse]:
    """Return only courses that are currently active or haven't started yet.

    A course is included if its end time hasn't passed yet, which naturally
    includes courses currently in progress.

    Args:
        courses: All today's courses
        now: Current datetime (defaults to datetime.now())

    Returns:
        Filtered list of upcoming and active courses
    """
    if now is None:
        now = datetime.now()

    today = now.date()
    result: list[TodayCourse] = []
    for c in courses:
        try:
            end = datetime.combine(today, datetime.strptime(c.end_time, "%H:%M").time())
        except (ValueError, TypeError):
            continue
        if end > now:
            result.append(c)
    return result
