"""Tests for today's courses parsing and filtering"""

import re
from datetime import datetime

import pytest

from custom_components.cosmos.api_client import CosmosClient
from custom_components.cosmos.const import BASE_URL
from custom_components.cosmos.models import TodayCourse
from custom_components.cosmos.utils import filter_upcoming_courses

SAMPLE_MEMBER_HOME_HTML = """
<html>
<body>
<div class="chartContainer">
    <div class="donut-size" percentage="45 %">
        <h5 class="chartlabel">Cosmos Stuttgart</h5>
        <h5 class="time">14:30</h5>
    </div>
</div>
<div id="okvPreview">
    <div class="previewData">
        <div>
            <span class="time">08:30 - 09:30</span>
            <span class="name">Fatburner Step</span>
            <div class="infoContainer">
                <span class="attendees" style="background: rgba(255, 255, 255, .4);"
                >11 Teilnehmer</span>
            </div>
            <div class="donut-size" id="course248121" percentage="34 %">
                ...donut chart SVG...
            </div>
        </div>
        <div>
            <span class="time">18:00 - 19:00</span>
            <span class="name">Yoga</span>
            <div class="infoContainer">
                <span class="attendees" style="background: rgba(255, 255, 255, .4);"
                >32 Teilnehmer</span>
            </div>
            <div class="donut-size" id="course378730" percentage="100 %">
                ...donut chart SVG...
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""


class TestGetTodayCourses:
    """Tests for get_today_courses via get_load"""

    @pytest.mark.asyncio
    async def test_parse_today_courses(self, mock_api, config):
        """Test parsing today's courses from member_home page"""
        login_url = f"{BASE_URL}/login"
        check_login_url = f"{BASE_URL}/check_login"
        member_home_url = f"{BASE_URL}/member_home"

        mock_api.get(
            re.compile(rf"^{re.escape(login_url)}\?"),
            status=200,
            headers={"Set-Cookie": "PHPSESSID=test_session_id"},
        )
        mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)
        mock_api.get(
            re.compile(rf"^{re.escape(member_home_url)}\?"),
            status=200,
            body=SAMPLE_MEMBER_HOME_HTML,
        )

        async with CosmosClient(config) as client:
            await client.login()
            load_data = await client.get_load()
            courses = load_data["today_courses"]

            assert len(courses) == 2

            # First course
            assert courses[0].course == "Fatburner Step"
            assert courses[0].participants == 11
            assert courses[0].percentage == pytest.approx(0.34)
            assert courses[0].start_time == "08:30"
            assert courses[0].end_time == "09:30"

            # Second course
            assert courses[1].course == "Yoga"
            assert courses[1].participants == 32
            assert courses[1].percentage == pytest.approx(1.0)
            assert courses[1].start_time == "18:00"
            assert courses[1].end_time == "19:00"

    @pytest.mark.asyncio
    async def test_no_okv_preview_returns_empty(self, mock_api, config):
        """Test that missing okvPreview section returns empty list"""
        login_url = f"{BASE_URL}/login"
        check_login_url = f"{BASE_URL}/check_login"
        member_home_url = f"{BASE_URL}/member_home"

        html_without_preview = """
        <html><body>
        <div class="chartContainer">
            <div class="donut-size" percentage="20 %">
                <h5 class="chartlabel">Cosmos</h5>
            </div>
        </div>
        </body></html>
        """

        mock_api.get(
            re.compile(rf"^{re.escape(login_url)}\?"),
            status=200,
            headers={"Set-Cookie": "PHPSESSID=test_session_id"},
        )
        mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)
        mock_api.get(
            re.compile(rf"^{re.escape(member_home_url)}\?"),
            status=200,
            body=html_without_preview,
        )

        async with CosmosClient(config) as client:
            await client.login()
            load_data = await client.get_load()
            courses = load_data["today_courses"]

            assert courses == []

    @pytest.mark.asyncio
    async def test_malformed_course_skipped(self, mock_api, config):
        """Test that course divs missing required fields are skipped"""
        login_url = f"{BASE_URL}/login"
        check_login_url = f"{BASE_URL}/check_login"
        member_home_url = f"{BASE_URL}/member_home"

        html_with_malformed = """
        <html><body>
        <div class="chartContainer">
            <div class="donut-size" percentage="20 %">
                <h5 class="chartlabel">Cosmos</h5>
            </div>
        </div>
        <div id="okvPreview">
            <div class="previewData">
                <div>
                    <span class="name">No Time Course</span>
                </div>
                <div>
                    <span class="time">10:00 - 11:00</span>
                    <span class="name">Valid Course</span>
                    <div class="infoContainer">
                        <span class="attendees">5 Teilnehmer</span>
                    </div>
                    <div class="donut-size" percentage="25 %"></div>
                </div>
            </div>
        </div>
        </body></html>
        """

        mock_api.get(
            re.compile(rf"^{re.escape(login_url)}\?"),
            status=200,
            headers={"Set-Cookie": "PHPSESSID=test_session_id"},
        )
        mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)
        mock_api.get(
            re.compile(rf"^{re.escape(member_home_url)}\?"),
            status=200,
            body=html_with_malformed,
        )

        async with CosmosClient(config) as client:
            await client.login()
            load_data = await client.get_load()
            courses = load_data["today_courses"]

            # Only the valid course should be returned
            assert len(courses) == 1
            assert courses[0].course == "Valid Course"


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
