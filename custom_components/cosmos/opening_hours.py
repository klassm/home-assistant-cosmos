"""Opening hours logic for Cosmos studio."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from functools import lru_cache

import holidays


@dataclass(frozen=True)
class OpeningHours:
    opening: datetime.time
    closing: datetime.time


_SUMMER_START = (5, 15)
_SUMMER_END = (10, 14)


def _is_summer_season(date: datetime.date) -> bool:
    month_day = (date.month, date.day)
    return _SUMMER_START <= month_day <= _SUMMER_END


@lru_cache(maxsize=3)
def _get_holidays(year: int) -> holidays.HolidayBase:
    by_holidays = holidays.country_holidays("DE", subdiv="BY", years=year)
    aug_holidays = holidays.country_holidays("DE", subdiv="Augsburg", years=year)
    by_holidays.update(aug_holidays)
    return by_holidays


_get_holidays(datetime.date.today().year)


def is_holiday(date: datetime.date) -> bool:
    return date in _get_holidays(date.year)


def get_todays_hours(date: datetime.date) -> OpeningHours:
    if is_holiday(date):
        if _is_summer_season(date):
            return OpeningHours(
                opening=datetime.time(8, 0), closing=datetime.time(18, 0)
            )
        return OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(20, 0))

    weekday = date.weekday()

    if weekday == 5:
        if _is_summer_season(date):
            return OpeningHours(
                opening=datetime.time(8, 0), closing=datetime.time(18, 0)
            )
        return OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(20, 0))

    if weekday == 6:
        return OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(20, 0))

    if weekday in (0, 2, 4):
        return OpeningHours(opening=datetime.time(7, 0), closing=datetime.time(22, 0))

    return OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(22, 0))
