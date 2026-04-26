"""Tests for Cosmos sensor logic"""

from __future__ import annotations

from custom_components.cosmos.models import TodayCourse


def _native_value(key: str, data: dict | None) -> int | str | None:
    """Replicate the native_value logic from CosmosSensor."""
    if data is None:
        return None
    if key == "load":
        return data.get("load", {}).get("percentage")
    if key == "total_participants":
        return sum(c.participants for c in data.get("today_courses", []))
    if key == "today_courses":
        return len(data.get("today_courses", []))
    return None


def _extra_state_attributes(key: str, data: dict | None) -> dict:
    """Replicate the extra_state_attributes logic from CosmosSensor."""
    if data is None:
        return {}
    if key == "today_courses":
        courses: list[TodayCourse] = data.get("today_courses", [])
        return {
            "courses": [
                {
                    "course": c.course,
                    "participants": c.participants,
                    "percentage": c.percentage,
                    "start_time": c.start_time,
                    "end_time": c.end_time,
                }
                for c in courses
            ],
        }
    return {}


class TestNativeValue:
    """Tests for sensor native_value logic"""

    def test_load(self):
        assert _native_value("load", {"load": {"percentage": 42}}) == 42

    def test_load_none_data(self):
        assert _native_value("load", None) is None

    def test_total_participants(self):
        courses = [
            TodayCourse(
                course="Yoga",
                participants=15,
                percentage=0.75,
                start_time="18:00",
                end_time="19:00",
            ),
            TodayCourse(
                course="Pilates",
                participants=8,
                percentage=0.4,
                start_time="19:30",
                end_time="20:30",
            ),
        ]
        assert (
            _native_value(
                "total_participants",
                {"load": {"percentage": 42}, "today_courses": courses},
            )
            == 23
        )

    def test_total_participants_empty(self):
        assert (
            _native_value(
                "total_participants",
                {"load": {"percentage": 0}, "today_courses": []},
            )
            == 0
        )

    def test_total_participants_none_data(self):
        assert _native_value("total_participants", None) is None

    def test_today_courses_count(self):
        courses = [
            TodayCourse(
                course="Yoga",
                participants=15,
                percentage=0.75,
                start_time="18:00",
                end_time="19:00",
            ),
        ]
        assert (
            _native_value(
                "today_courses",
                {"load": {"percentage": 42}, "today_courses": courses},
            )
            == 1
        )

    def test_today_courses_count_empty(self):
        assert (
            _native_value(
                "today_courses",
                {"load": {"percentage": 0}, "today_courses": []},
            )
            == 0
        )


class TestExtraStateAttributes:
    """Tests for sensor extra_state_attributes logic"""

    def test_today_courses_attributes(self):
        courses = [
            TodayCourse(
                course="Yoga",
                participants=15,
                percentage=0.75,
                start_time="18:00",
                end_time="19:00",
            ),
            TodayCourse(
                course="Pilates",
                participants=8,
                percentage=0.4,
                start_time="19:30",
                end_time="20:30",
            ),
        ]
        attrs = _extra_state_attributes(
            "today_courses",
            {"load": {"percentage": 42}, "today_courses": courses},
        )

        assert "courses" in attrs
        assert len(attrs["courses"]) == 2

        yoga = attrs["courses"][0]
        assert yoga["course"] == "Yoga"
        assert yoga["participants"] == 15
        assert yoga["percentage"] == 0.75
        assert yoga["start_time"] == "18:00"
        assert yoga["end_time"] == "19:00"

    def test_today_courses_empty(self):
        attrs = _extra_state_attributes(
            "today_courses",
            {"load": {"percentage": 42}, "today_courses": []},
        )
        assert attrs["courses"] == []

    def test_today_courses_none_data(self):
        attrs = _extra_state_attributes("today_courses", None)
        assert attrs == {}

    def test_load_no_attributes(self):
        attrs = _extra_state_attributes(
            "load",
            {"load": {"percentage": 42}, "today_courses": []},
        )
        assert attrs == {}

    def test_total_participants_no_attributes(self):
        attrs = _extra_state_attributes(
            "total_participants",
            {"load": {"percentage": 42}, "today_courses": []},
        )
        assert attrs == {}
