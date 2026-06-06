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

    @property
    def is_closed(self) -> bool:
        return self.opening == self.closing


_SUMMER_START = (5, 15)
_SUMMER_END = (10, 14)

_CLOSED = OpeningHours(opening=datetime.time(0, 0), closing=datetime.time(0, 0))

_HOLIDAY_HOURS: dict[str, OpeningHours] = {
    "New Year's Day": _CLOSED,
    "Epiphany": OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(20, 0)),
    "Good Friday": OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(20, 0)),
    "Easter Monday": OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(20, 0)),
    "Labor Day": OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(20, 0)),
    "Ascension Day": OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(18, 0)),
    "Whit Monday": OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(18, 0)),
    "Corpus Christi": OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(18, 0)),
    "German Unity Day": OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(18, 0)),
    "All Saints' Day": OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(20, 0)),
    "Christmas Day": _CLOSED,
    "Second Day of Christmas": OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(20, 0)),
}

_ADDITIONAL_HOLIDAYS: dict[tuple[int, int], OpeningHours] = {
    (8, 15): OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(18, 0)),
    (12, 24): OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(14, 0)),
    (12, 31): OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(14, 0)),
}


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
    return date in _get_holidays(date.year) or (date.month, date.day) in _ADDITIONAL_HOLIDAYS


def get_todays_hours(date: datetime.date) -> OpeningHours:
    additional = _ADDITIONAL_HOLIDAYS.get((date.month, date.day))
    if additional is not None:
        return additional

    hol = _get_holidays(date.year)
    if date in hol:
        name = hol[date]
        if name in _HOLIDAY_HOURS:
            return _HOLIDAY_HOURS[name]
        if _is_summer_season(date):
            return OpeningHours(opening=datetime.time(8, 0), closing=datetime.time(18, 0))
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
