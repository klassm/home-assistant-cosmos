"""Tests for today's courses filtering"""

from datetime import datetime

from custom_components.cosmos.models import TodayCourse
from custom_components.cosmos.utils import filter_upcoming_courses


class TestFilterUpcomingCourses:
    """Tests for filter_upcoming_courses function"""

    def test_filters_past_courses(self):
        """Test that past courses are filtered out"""
        courses = [
            TodayCourse(
                course="Morning Yoga",
                participants=10,
                percentage=0.5,
                start_time="08:30",
                end_time="09:30",
            ),
            TodayCourse(
                course="Evening Pilates",
                participants=15,
                percentage=0.75,
                start_time="17:00",
                end_time="18:00",
            ),
            TodayCourse(
                course="Late Spin",
                participants=20,
                percentage=1.0,
                start_time="18:00",
                end_time="19:00",
            ),
        ]

        # now=17:30: 08:30-09:30 past, 17:00-18:00 active, 18:00-19:00 upcoming
        now = datetime(2026, 4, 14, 17, 30)
        upcoming = filter_upcoming_courses(courses, now)

        assert len(upcoming) == 2
        assert upcoming[0].course == "Evening Pilates"
        assert upcoming[1].course == "Late Spin"

    def test_returns_all_when_all_upcoming(self):
        """Test that all courses are returned when all are upcoming"""
        courses = [
            TodayCourse(
                course="Yoga",
                participants=10,
                percentage=0.5,
                start_time="18:00",
                end_time="19:00",
            ),
        ]

        now = datetime(2026, 4, 14, 8, 0)
        upcoming = filter_upcoming_courses(courses, now)

        assert len(upcoming) == 1

    def test_returns_empty_when_all_past(self):
        """Test that no courses are returned when all are past"""
        courses = [
            TodayCourse(
                course="Morning Yoga",
                participants=10,
                percentage=0.5,
                start_time="08:00",
                end_time="09:00",
            ),
        ]

        now = datetime(2026, 4, 14, 10, 0)
        upcoming = filter_upcoming_courses(courses, now)

        assert len(upcoming) == 0

    def test_active_course_included(self):
        """Test that a currently active course is included"""
        courses = [
            TodayCourse(
                course="Yoga",
                participants=10,
                percentage=0.5,
                start_time="17:00",
                end_time="18:00",
            ),
        ]

        # Course is 17:00-18:00, now is 17:30 — still active
        now = datetime(2026, 4, 14, 17, 30)
        upcoming = filter_upcoming_courses(courses, now)

        assert len(upcoming) == 1

    def test_course_ending_exactly_now_excluded(self):
        """Test that a course ending exactly now is excluded"""
        courses = [
            TodayCourse(
                course="Yoga",
                participants=10,
                percentage=0.5,
                start_time="17:00",
                end_time="18:00",
            ),
        ]

        # Course ends at 18:00, now is 18:00 — no longer upcoming
        now = datetime(2026, 4, 14, 18, 0)
        upcoming = filter_upcoming_courses(courses, now)

        assert len(upcoming) == 0

    def test_defaults_to_now(self):
        """Test that now defaults to datetime.now()"""
        # Just verify it doesn't crash and returns a list
        courses = [
            TodayCourse(
                course="Future",
                participants=5,
                percentage=0.25,
                start_time="23:00",
                end_time="23:59",
            ),
        ]
        result = filter_upcoming_courses(courses)
        assert isinstance(result, list)

    def test_malformed_end_time_skipped(self):
        """Regression test: malformed end_time should be skipped, not raise

        Before the fix, datetime.strptime(c.end_time, "%H:%M") would raise
        ValueError on unexpected formats, propagating up and killing the
        entire coordinator update (including load data).
        """
        courses = [
            TodayCourse(
                course="Bad Time",
                participants=10,
                percentage=0.5,
                start_time="08:00",
                end_time="not-a-time",
            ),
            TodayCourse(
                course="Good Course",
                participants=15,
                percentage=0.75,
                start_time="18:00",
                end_time="19:00",
            ),
        ]

        now = datetime(2026, 4, 14, 17, 0)
        upcoming = filter_upcoming_courses(courses, now)

        assert len(upcoming) == 1
        assert upcoming[0].course == "Good Course"

    def test_empty_end_time_skipped(self):
        """Test that empty end_time is skipped gracefully"""
        courses = [
            TodayCourse(
                course="Empty End",
                participants=5,
                percentage=0.25,
                start_time="10:00",
                end_time="",
            ),
        ]

        now = datetime(2026, 4, 14, 8, 0)
        upcoming = filter_upcoming_courses(courses, now)

        assert len(upcoming) == 0
