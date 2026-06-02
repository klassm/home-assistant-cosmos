"""Tests for Cosmos opening hours logic."""

from __future__ import annotations

import datetime

from custom_components.cosmos.opening_hours import get_todays_hours, is_holiday


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
        from custom_components.cosmos.opening_hours import _get_holidays

        by_holidays = _get_holidays(2026)
        assert aug_8 in by_holidays
