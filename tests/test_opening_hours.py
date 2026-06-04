"""Tests for Cosmos opening hours logic."""

from __future__ import annotations

import asyncio
import datetime

from custom_components.cosmos.opening_hours import (
    _get_holidays,
    get_todays_hours,
    is_holiday,
)


class TestWeekdaySchedule:
    def test_monday(self):
        hours = get_todays_hours(datetime.date(2026, 6, 1))
        assert hours.opening == datetime.time(7, 0)
        assert hours.closing == datetime.time(22, 0)

    def test_wednesday(self):
        hours = get_todays_hours(datetime.date(2026, 6, 3))
        assert hours.opening == datetime.time(7, 0)
        assert hours.closing == datetime.time(22, 0)

    def test_friday(self):
        hours = get_todays_hours(datetime.date(2026, 6, 5))
        assert hours.opening == datetime.time(7, 0)
        assert hours.closing == datetime.time(22, 0)

    def test_tuesday(self):
        hours = get_todays_hours(datetime.date(2026, 6, 2))
        assert hours.opening == datetime.time(8, 0)
        assert hours.closing == datetime.time(22, 0)

    def test_thursday_non_holiday(self):
        hours = get_todays_hours(datetime.date(2026, 6, 11))
        assert hours.opening == datetime.time(8, 0)
        assert hours.closing == datetime.time(22, 0)

    def test_sunday(self):
        hours = get_todays_hours(datetime.date(2026, 6, 7))
        assert hours.opening == datetime.time(8, 0)
        assert hours.closing == datetime.time(20, 0)


class TestSaturdaySchedule:
    def test_saturday_summer(self):
        hours = get_todays_hours(datetime.date(2026, 7, 4))
        assert hours.opening == datetime.time(8, 0)
        assert hours.closing == datetime.time(18, 0)

    def test_saturday_winter(self):
        hours = get_todays_hours(datetime.date(2026, 11, 7))
        assert hours.opening == datetime.time(8, 0)
        assert hours.closing == datetime.time(20, 0)

    def test_saturday_season_boundary_may_15(self):
        hours = get_todays_hours(datetime.date(2026, 5, 16))
        assert hours.closing == datetime.time(18, 0)

    def test_saturday_season_boundary_oct_14(self):
        hours = get_todays_hours(datetime.date(2026, 10, 10))
        assert hours.closing == datetime.time(18, 0)

    def test_saturday_season_boundary_oct_15(self):
        hours = get_todays_hours(datetime.date(2026, 10, 17))
        assert hours.closing == datetime.time(20, 0)


class TestHolidaySchedule:
    def test_friedensfest_aug_8_summer(self):
        assert is_holiday(datetime.date(2026, 8, 8))
        hours = get_todays_hours(datetime.date(2026, 8, 8))
        assert hours.opening == datetime.time(8, 0)
        assert hours.closing == datetime.time(18, 0)

    def test_corpus_christi_summer(self):
        assert is_holiday(datetime.date(2026, 6, 4))
        hours = get_todays_hours(datetime.date(2026, 6, 4))
        assert hours.opening == datetime.time(8, 0)
        assert hours.closing == datetime.time(18, 0)

    def test_christmas_winter(self):
        assert is_holiday(datetime.date(2026, 12, 25))
        hours = get_todays_hours(datetime.date(2026, 12, 25))
        assert hours.opening == datetime.time(8, 0)
        assert hours.closing == datetime.time(20, 0)

    def test_holiday_on_sunday_uses_holiday_hours(self):
        all_saints = datetime.date(2026, 11, 1)
        assert all_saints.weekday() == 6
        assert is_holiday(all_saints)
        hours = get_todays_hours(all_saints)
        assert hours.opening == datetime.time(8, 0)
        assert hours.closing == datetime.time(20, 0)

    def test_not_holiday(self):
        assert not is_holiday(datetime.date(2026, 6, 1))


class TestHolidaySpecificity:
    def test_friedensfest_is_augsburg_only(self):
        aug_8 = datetime.date(2026, 8, 8)
        by_holidays = _get_holidays(2026)
        assert aug_8 in by_holidays


class TestGetHolidaysCaching:
    def test_same_year_returns_cached_object(self):
        result1 = _get_holidays(2026)
        result2 = _get_holidays(2026)
        assert result1 is result2

    def test_different_years_return_different_objects(self):
        result1 = _get_holidays(2025)
        result2 = _get_holidays(2026)
        assert result1 is not result2

    def test_cache_is_bounded(self):
        _get_holidays.cache_clear()
        for year in range(2020, 2025):
            _get_holidays(year)
        _get_holidays(2025)
        cache_info = _get_holidays.cache_info()
        assert cache_info.currsize <= 3
        _get_holidays.cache_clear()

    def test_current_year_preloaded(self):
        _get_holidays.cache_clear()
        import importlib

        import custom_components.cosmos.opening_hours as oh_mod

        importlib.reload(oh_mod)
        current_year = datetime.date.today().year
        cache_info = oh_mod._get_holidays.cache_info()
        assert cache_info.currsize >= 1
        oh_mod._get_holidays(current_year)
        after_info = oh_mod._get_holidays.cache_info()
        assert after_info.hits > 0


class TestGetTodaysHoursAsyncSafe:
    async def test_works_in_async_executor(self):
        loop = asyncio.get_event_loop()
        today = datetime.date.today()
        result = await loop.run_in_executor(None, get_todays_hours, today)
        assert result.opening is not None
        assert result.closing is not None
        assert result.closing > result.opening

    async def test_holiday_check_async_safe(self):
        loop = asyncio.get_event_loop()
        christmas = datetime.date(2026, 12, 25)
        result = await loop.run_in_executor(None, is_holiday, christmas)
        assert result is True
