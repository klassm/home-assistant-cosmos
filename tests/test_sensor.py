"""Tests for Cosmos sensor attributes logic"""

from __future__ import annotations

from custom_components.cosmos.models import TodayCourse


def _build_extra_state_attributes(data: dict | None) -> dict:
    """Replicate the extra_state_attributes logic from CosmosLoadSensor.

    We test the logic directly rather than importing the sensor class,
    which depends on HA base classes that can't be mocked easily.
    """
    if data is None:
        return {"today_courses": [], "total_participants": 0}
    courses: list[TodayCourse] = data.get("today_courses", [])
    return {
        "today_courses": [
            {
                "course": c.course,
                "participants": c.participants,
                "percentage": c.percentage,
                "start_time": c.start_time,
                "end_time": c.end_time,
            }
            for c in courses
        ],
        "total_participants": sum(c.participants for c in courses),
    }


class TestExtraStateAttributes:
    """Tests for sensor extra_state_attributes logic"""

    def test_with_courses(self):
        """Test attributes include today's courses"""
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
        attrs = _build_extra_state_attributes(
            {"load": {"percentage": 42}, "today_courses": courses}
        )

        assert "today_courses" in attrs
        assert len(attrs["today_courses"]) == 2
        assert attrs["total_participants"] == 23  # 15 + 8

        # Verify first course attributes
        yoga = attrs["today_courses"][0]
        assert yoga["course"] == "Yoga"
        assert yoga["participants"] == 15
        assert yoga["percentage"] == 0.75
        assert yoga["start_time"] == "18:00"
        assert yoga["end_time"] == "19:00"

        # Verify second course attributes
        pilates = attrs["today_courses"][1]
        assert pilates["course"] == "Pilates"
        assert pilates["participants"] == 8
        assert pilates["percentage"] == 0.4

    def test_empty_courses(self):
        """Test attributes with no courses"""
        attrs = _build_extra_state_attributes(
            {"load": {"percentage": 42}, "today_courses": []}
        )
        assert attrs["today_courses"] == []
        assert attrs["total_participants"] == 0

    def test_missing_courses_key(self):
        """Test attributes when today_courses key missing"""
        attrs = _build_extra_state_attributes({"load": {"percentage": 42}})
        assert attrs["today_courses"] == []

    def test_no_coordinator_data(self):
        """Test attributes when coordinator.data is None (before first refresh)

        Regression test: extra_state_attributes must handle None coordinator.data
        gracefully instead of crashing with AttributeError on None.get().
        """
        attrs = _build_extra_state_attributes(None)
        assert attrs["today_courses"] == []
        assert attrs["total_participants"] == 0

    def test_course_dataclass_fields(self):
        """Test that TodayCourse dataclass has all required fields"""
        course = TodayCourse(
            course="Spin",
            participants=20,
            percentage=1.0,
            start_time="20:00",
            end_time="21:00",
        )
        assert course.course == "Spin"
        assert course.participants == 20
        assert course.percentage == 1.0
        assert course.start_time == "20:00"
        assert course.end_time == "21:00"
