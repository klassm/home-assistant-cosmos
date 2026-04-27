"""Tests for API client"""

import re

import pytest
from bs4 import BeautifulSoup

from custom_components.cosmos.api_client import CosmosClient
from custom_components.cosmos.const import BASE_URL
from custom_components.cosmos.exceptions import (
    AuthenticationError,
    BookingError,
)
from custom_components.cosmos.models import BookedCourse, TodayCourse


@pytest.mark.asyncio
async def test_login_success(mock_api, config):
    """Test successful login"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"

    # Mock login page - returns session cookie
    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id; path=/"},
    )

    # Mock check_login with success
    mock_api.post(
        re.compile(rf"^{re.escape(check_login_url)}\?"),
        status=200,
        body="Login successful",
    )

    async with CosmosClient(config) as client:
        session_id = await client.login()
        assert session_id == "test_session_id"


@pytest.mark.asyncio
async def test_login_invalid_credentials(mock_api, config):
    """Test login with invalid credentials"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(
        re.compile(rf"^{re.escape(check_login_url)}\?"),
        status=200,
        body="Anmeldung fehlgeschlagen",
    )

    async with CosmosClient(config) as client:
        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            await client.login()


@pytest.mark.asyncio
async def test_login_page_failure(mock_api, config):
    """Test login when login page returns error"""
    login_url = f"{BASE_URL}/login"

    mock_api.get(re.compile(rf"^{re.escape(login_url)}"), status=500)

    async with CosmosClient(config) as client:
        with pytest.raises(AuthenticationError, match="Login page failed"):
            await client.login()


@pytest.mark.asyncio
async def test_login_no_session_cookie(mock_api, config):
    """Test login when no session cookie is returned"""
    login_url = f"{BASE_URL}/login"

    mock_api.get(re.compile(rf"^{re.escape(login_url)}"), status=200, headers={})

    async with CosmosClient(config) as client:
        with pytest.raises(AuthenticationError, match="No session cookie"):
            await client.login()


@pytest.mark.asyncio
async def test_get_mandant_data(mock_api, config):
    """Test getting mandant data"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"
    mycourses_url = f"{BASE_URL}/mycourses"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)

    # Mock mycourses page with mandant data and booked courses
    # Includes realistic HTML with storno cells that also have showformediumup class
    html = """
    <html>
        <div id="jsvariable-data-mandantData"
             data-mandantdata='{"loginToken":"token123"}'></div>
        <div id="jsvariable-data-memberData"
              data-memberdata='{"nr":"12345"}'></div>
        <div class="columns small-12 futureBookings">
            <h3 class="themeColorLight">Zukünftige Buchungen (<span>2</span>)</h3>
            <table><tbody>
                <tr class="future header">
                    <th class="future themeFontColorLight">Name</th>
                </tr>
                <tr booktype="single" group="43" id="161948" class="swipeable future 0">
                    <td><span class="showformobileonly">30.04.26</span><span class="courseName">RückenFit</span></td>
                    <td class="showformediumup">Do 30.04.26</td>
                    <td>09:15 - 10:00</td>
                    <td class="showforlargeup">Kursraum</td>
                    <td class="showforlargeup">Susa</td>
                    <td>0,00€</td>
                    <td class="showforlargeup">26.04.2026</td>
                    <td class="storno showformobileonly">Storno</td>
                    <td class="storno showformediumup">Stornieren</td>
                </tr>
                <tr booktype="single" group="51" id="154801" class="swipeable future 1">
                    <td><span class="showformobileonly">29.04.26</span><span class="courseName">Bauch Beine Po</span></td>
                    <td class="showformediumup">Mi 29.04.26</td>
                    <td>08:45 - 09:45</td>
                    <td class="showforlargeup">Kursraum</td>
                    <td class="showforlargeup">Birgit</td>
                    <td>0,00€</td>
                    <td class="showforlargeup">25.04.2026</td>
                    <td class="storno showformobileonly">Storno</td>
                    <td class="storno showformediumup">Stornieren</td>
                </tr>
            </tbody></table>
        </div>
    </html>
    """
    mock_api.get(re.compile(rf"^{re.escape(mycourses_url)}\?"), status=200, body=html)

    async with CosmosClient(config) as client:
        await client.login()
        mandant_data, booked = await client.get_mandant_data()

        assert mandant_data.login_token == "token123"
        assert mandant_data.member_nr == "12345"
        assert len(booked) == 2
        assert booked[0].name == "RückenFit"
        assert booked[0].date == "Do 30.04.26"
        assert booked[0].time == "09:15 - 10:00"
        assert booked[1].name == "Bauch Beine Po"


@pytest.mark.asyncio
async def test_get_mandant_data_missing_element(mock_api, config):
    """Test get_mandant_data when element is missing"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"
    mycourses_url = f"{BASE_URL}/mycourses"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)

    # Missing mandant data element
    html = "<html><body>No data here</body></html>"
    mock_api.get(re.compile(rf"^{re.escape(mycourses_url)}\?"), status=200, body=html)

    async with CosmosClient(config) as client:
        await client.login()
        with pytest.raises(BookingError, match="Cannot find mandantData element"):
            await client.get_mandant_data()


@pytest.mark.asyncio
async def test_get_mandant_data_not_logged_in(mock_api, config):
    """Test get_mandant_data without login"""
    async with CosmosClient(config) as client:
        with pytest.raises(AuthenticationError, match="Not logged in"):
            await client.get_mandant_data()


@pytest.mark.asyncio
async def test_find_courses(mock_api, config):
    """Test finding courses"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)

    # Mock proxy response with courses
    courses_data = {
        "courses": [
            {
                "nr": 1,
                "course_name": "Yoga",
                "begin": "2024-01-15T18:00:00",
                "end": "2024-01-15T19:00:00",
                "booked": 0,
                "online_book_max": 10,
                "course_nr": 101,
            }
        ]
    }
    # Match any proxy.php URL
    mock_api.get(
        re.compile(rf"^{re.escape(BASE_URL)}/proxy\.php"),
        status=200,
        payload=courses_data,
    )

    async with CosmosClient(config) as client:
        await client.login()
        courses = await client.find_courses(member_nr="12345", login_token="token")

        assert len(courses) == 1
        assert courses[0].course_name == "Yoga"


@pytest.mark.asyncio
async def test_find_courses_empty(mock_api, config):
    """Test finding courses when none available"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)

    mock_api.get(
        re.compile(rf"^{re.escape(BASE_URL)}/proxy\.php"),
        status=200,
        payload={"courses": []},
    )

    async with CosmosClient(config) as client:
        await client.login()
        courses = await client.find_courses(member_nr="12345", login_token="token")

        assert len(courses) == 0


@pytest.mark.asyncio
async def test_is_already_booked_true(mock_api, config):
    """Test checking if course is already booked (true)"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)

    # Mock booked courses response
    booked_data = {
        "booked_courses": [
            {"t601_lfnr": 1},
            {"t601_lfnr": 2},
        ]
    }
    mock_api.get(
        re.compile(rf"^{re.escape(BASE_URL)}/proxy\.php"),
        status=200,
        payload=booked_data,
    )

    async with CosmosClient(config) as client:
        await client.login()

        from custom_components.cosmos.models import Course

        course = Course(
            nr=1,
            course_name="Yoga",
            begin="2024-01-15T18:00:00",
            end="2024-01-15T19:00:00",
            booked=0,
            online_book_max=10,
        )

        result = await client.is_already_booked(
            course=course, member_nr="12345", login_token="token"
        )
        assert result is True


@pytest.mark.asyncio
async def test_is_already_booked_false(mock_api, config):
    """Test checking if course is already booked (false)"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)

    mock_api.get(
        re.compile(rf"^{re.escape(BASE_URL)}/proxy\.php"),
        status=200,
        payload={"booked_courses": [{"t601_lfnr": 999}]},
    )

    async with CosmosClient(config) as client:
        await client.login()

        from custom_components.cosmos.models import Course

        course = Course(
            nr=1,
            course_name="Yoga",
            begin="2024-01-15T18:00:00",
            end="2024-01-15T19:00:00",
            booked=0,
            online_book_max=10,
        )

        result = await client.is_already_booked(
            course=course, member_nr="12345", login_token="token"
        )
        assert result is False


@pytest.mark.asyncio
async def test_book_course_success(mock_api, config):
    """Test successful course booking"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"
    agb_url = f"{BASE_URL}/newmember/agb"
    accepted_url = f"{BASE_URL}/memberagbaccepted"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)
    # AGB page returns HTML with "AGB akzeptieren" button text
    mock_api.post(
        re.compile(rf"^{re.escape(agb_url)}"),
        status=200,
        body="<html><body><button>AGB akzeptieren</button></body></html>",
    )
    mock_api.post(
        re.compile(rf"^{re.escape(accepted_url)}"),
        status=200,
        body="Vielen Dank und wir freuen uns auf deinen Besuch!",
    )

    async with CosmosClient(config) as client:
        await client.login()

        from custom_components.cosmos.models import Course

        course = Course(
            nr=1,
            course_name="Yoga",
            begin="2024-01-15T18:00:00",
            end="2024-01-15T19:00:00",
            booked=0,
            online_book_max=10,
            course_period_begin="2024-01-01",
            course_period_end="2024-12-31",
            course_price_single="10.00",
            course_nr=101,
            book_type="online",
        )

        result = await client.book_course(course)
        assert result == "Successfully booked"


@pytest.mark.asyncio
async def test_book_course_failure(mock_api, config):
    """Test course booking failure"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"
    agb_url = f"{BASE_URL}/newmember/agb"
    accepted_url = f"{BASE_URL}/memberagbaccepted"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)
    # AGB page returns HTML with "AGB akzeptieren" button text
    mock_api.post(
        re.compile(rf"^{re.escape(agb_url)}"),
        status=200,
        body="<html><body><button>AGB akzeptieren</button></body></html>",
    )
    mock_api.post(
        re.compile(rf"^{re.escape(accepted_url)}"),
        status=200,
        body="Something went wrong",
    )

    async with CosmosClient(config) as client:
        await client.login()

        from custom_components.cosmos.models import Course

        course = Course(
            nr=1,
            course_name="Yoga",
            begin="2024-01-15T18:00:00",
            end="2024-01-15T19:00:00",
            booked=0,
            online_book_max=10,
        )

        with pytest.raises(BookingError, match="Booking failed"):
            await client.book_course(course)


@pytest.mark.asyncio
async def test_book_course_not_logged_in(mock_api, config):
    """Test booking without login"""
    async with CosmosClient(config) as client:
        from custom_components.cosmos.models import Course

        course = Course(
            nr=1,
            course_name="Yoga",
            begin="2024-01-15T18:00:00",
            end="2024-01-15T19:00:00",
            booked=0,
            online_book_max=10,
        )

        with pytest.raises(AuthenticationError, match="Not logged in"):
            await client.book_course(course)


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager"""
    from custom_components.cosmos.models import Config

    config = Config(username="test", password="test", mandant="test_mandant")

    async with CosmosClient(config) as client:
        assert client.session is not None

    # Session should be closed after context exit
    assert client.session is None


@pytest.mark.asyncio
async def test_require_session_without_context():
    """Test that operations fail without context manager"""
    from custom_components.cosmos.models import Config

    config = Config(username="test", password="test", mandant="test_mandant")
    client = CosmosClient(config)

    with pytest.raises(RuntimeError, match="Use async context manager"):
        await client.login()


BOOKING_LIST_HTML = """
<html>
<body>
<div id="bookingList" offset="0">
    <div class="columns small-12 futureBookings">
        <h3 class="themeColorLight">Zukünftige Buchungen (<span>2</span>)</h3>
        <table><tbody>
            <tr class="future header">
                <th class="future themeFontColorLight">Name</th>
            </tr>
            <tr booktype="single" group="43" id="161948" class="swipeable future 0">
                <td><span class="showformobileonly">30.04.26</span><span class="courseName">RückenFit</span></td>
                <td class="showformediumup">Do 30.04.26</td>
                <td>09:15 - 10:00</td>
                <td class="showforlargeup">Kursraum</td>
                <td class="showforlargeup">Susa</td>
                <td>0,00€</td>
                <td class="showforlargeup">26.04.2026</td>
                <td class="storno showformobileonly">Storno</td>
                <td class="storno showformediumup">Stornieren</td>
            </tr>
            <tr booktype="single" group="51" id="154801" class="swipeable future 1">
                <td><span class="showformobileonly">29.04.26</span><span class="courseName">Bauch Beine Po</span></td>
                <td class="showformediumup">Mi 29.04.26</td>
                <td>08:45 - 09:45</td>
                <td class="showforlargeup">Kursraum</td>
                <td class="showforlargeup">Birgit</td>
                <td>0,00€</td>
                <td class="showforlargeup">25.04.2026</td>
                <td class="storno showformobileonly">Storno</td>
                <td class="storno showformediumup">Stornieren</td>
            </tr>
        </tbody></table>
    </div>
    <div class="columns small-12 waitlist invisible">
        <h3 class="themeColorLight">Warteliste (<span>0</span>)</h3>
    </div>
    <div class="columns small-12 pastBookings">
        <h3 class="themeColorLight">Vergangene Buchungen (<span>453</span>)</h3>
        <table><tbody>
            <tr class="past header">
                <th class="past themeFontColorLight">Name</th>
            </tr>
            <tr booktype="completesingle" id="161947" class="swipeable past 0">
                <td><span class="showformobileonly">26.04.26</span><span class="courseName">RückenFit</span></td>
                <td class="showformediumup">Sa 26.04.26</td>
                <td>09:15 - 10:00</td>
                <td class="showforlargeup">Kursraum</td>
                <td class="showforlargeup">Susa</td>
                <td>0,00€</td>
            </tr>
            <tr booktype="single" id="161738" class="swipeable past 1">
                <td><span class="showformobileonly">25.04.26</span><span class="courseName">Pilates</span></td>
                <td class="showformediumup">Fr 25.04.26</td>
                <td>08:45 - 09:45</td>
                <td class="showforlargeup">Kursraum</td>
                <td class="showforlargeup"></td>
                <td>0,00€</td>
            </tr>
            <tr booktype="single" id="161737" class="swipeable past 2">
                <td><span class="showformobileonly">24.04.26</span><span class="courseName">Step &amp; Cardio</span></td>
                <td class="showformediumup">Do 24.04.26</td>
                <td>18:30 - 19:30</td>
                <td class="showforlargeup">Kursraum</td>
                <td class="showforlargeup"></td>
                <td>0,00€</td>
            </tr>
            <tr booktype="single" id="392040" class="swipeable past 3 invisible">
                <td><span class="showformobileonly">01.03.20</span><span class="courseName">Yoga</span></td>
                <td class="showformediumup">So 01.03.20</td>
                <td>10:00 - 11:00</td>
                <td class="showforlargeup">Kursraum</td>
                <td class="showforlargeup"></td>
                <td>0,00€</td>
            </tr>
        </tbody></table>
        <a class="loadMoreButton" onclick="showMoreUserCourses(event)">Mehr anzeigen</a>
    </div>
</div>
</body>
</html>
"""

OKV_PREVIEW_HTML = """
<html>
<body>
<div id="okvPreview">
    <div class="previewData">
        <div>
            <span class="time">09:15 - 10:00</span>
            <span class="name">RückenFit</span>
            <span class="attendees">11 Teilnehmer</span>
            <div class="donut-size" percentage="100 %" id="course247176">
                <p class="text-center donut-data"><span>11</span>/11</p>
            </div>
        </div>
        <div>
            <span class="time">08:45 - 09:45</span>
            <span class="name">Bauch Beine Po</span>
            <span class="attendees">8 Teilnehmer</span>
            <div class="donut-size" percentage="80 %" id="course247175">
                <p class="text-center donut-data"><span>8</span>/10</p>
            </div>
        </div>
        <div>
            <span class="time">18:30 - 19:30</span>
            <span class="name">Step &amp; Cardio</span>
            <span class="attendees">5 Teilnehmer</span>
            <div class="donut-size" percentage="34 %" id="course247180">
                <p class="text-center donut-data"><span>5</span>/15</p>
            </div>
        </div>
        <div>
            <span class="time">10:15 - 11:00</span>
            <span class="name">Mobility</span>
            <span class="attendees">0 Teilnehmer</span>
            <div class="donut-size" percentage="0 %" id="course247177">
                <p class="text-center donut-data"><span>0</span>/12</p>
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""


class TestParseBookedCourses:
    def test_parses_future_bookings(self):
        soup = BeautifulSoup(BOOKING_LIST_HTML, "html.parser")
        result = CosmosClient._parse_booked_courses(soup)

        assert len(result) == 2
        assert result[0] == BookedCourse(
            name="RückenFit", date="Do 30.04.26", time="09:15 - 10:00"
        )
        assert result[1] == BookedCourse(
            name="Bauch Beine Po", date="Mi 29.04.26", time="08:45 - 09:45"
        )

    def test_excludes_storno_cells_from_date(self):
        soup = BeautifulSoup(BOOKING_LIST_HTML, "html.parser")
        result = CosmosClient._parse_booked_courses(soup)

        for course in result:
            assert "Storn" not in course.date

    def test_returns_empty_when_no_future_bookings(self):
        html = '<html><div class="columns small-12 futureBookings"><h3>Zukünftige Buchungen (<span>0</span>)</h3></div></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = CosmosClient._parse_booked_courses(soup)

        assert result == []

    def test_returns_empty_when_no_future_bookings_div(self):
        html = "<html><body>No booking list</body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = CosmosClient._parse_booked_courses(soup)

        assert result == []

    def test_skips_rows_missing_name(self):
        html = """
        <html><div class="futureBookings"><table><tbody>
            <tr class="swipeable future">
                <td class="showformediumup">Do 30.04.26</td>
                <td>09:15 - 10:00</td>
            </tr>
        </tbody></table></div></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = CosmosClient._parse_booked_courses(soup)

        assert result == []

    def test_skips_rows_with_too_few_tds(self):
        html = """
        <html><div class="futureBookings"><table><tbody>
            <tr class="swipeable future">
                <td><span class="courseName">Yoga</span></td>
            </tr>
        </tbody></table></div></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = CosmosClient._parse_booked_courses(soup)

        assert result == []


class TestParseTodayCourses:
    def test_parses_today_upcoming_courses(self):
        soup = BeautifulSoup(OKV_PREVIEW_HTML, "html.parser")
        result = CosmosClient._parse_today_upcoming_courses(soup)

        assert len(result) == 4
        assert result[0] == TodayCourse(
            course="RückenFit",
            participants=11,
            percentage=1.0,
            start_time="09:15",
            end_time="10:00",
        )
        assert result[1] == TodayCourse(
            course="Bauch Beine Po",
            participants=8,
            percentage=0.8,
            start_time="08:45",
            end_time="09:45",
        )
        assert result[2] == TodayCourse(
            course="Step & Cardio",
            participants=5,
            percentage=0.34,
            start_time="18:30",
            end_time="19:30",
        )
        assert result[3] == TodayCourse(
            course="Mobility",
            participants=0,
            percentage=0.0,
            start_time="10:15",
            end_time="11:00",
        )

    def test_handles_zero_participants(self):
        soup = BeautifulSoup(OKV_PREVIEW_HTML, "html.parser")
        result = CosmosClient._parse_today_upcoming_courses(soup)

        mobility = [c for c in result if c.course == "Mobility"][0]
        assert mobility.participants == 0
        assert mobility.percentage == 0.0

    def test_returns_empty_when_no_okv_preview(self):
        html = "<html><body>No preview section</body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = CosmosClient._parse_today_upcoming_courses(soup)

        assert result == []

    def test_returns_empty_when_no_preview_data(self):
        html = '<html><div id="okvPreview"></div></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = CosmosClient._parse_today_upcoming_courses(soup)

        assert result == []

    def test_skips_courses_without_name(self):
        html = """
        <html><div id="okvPreview"><div class="previewData">
            <div>
                <span class="time">09:15 - 10:00</span>
                <span class="attendees">5 Teilnehmer</span>
                <div class="donut-size" percentage="50 %"></div>
            </div>
        </div></div></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = CosmosClient._parse_today_upcoming_courses(soup)

        assert result == []

    def test_skips_courses_without_time(self):
        html = """
        <html><div id="okvPreview"><div class="previewData">
            <div>
                <span class="name">Yoga</span>
                <span class="attendees">5 Teilnehmer</span>
                <div class="donut-size" percentage="50 %"></div>
            </div>
        </div></div></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = CosmosClient._parse_today_upcoming_courses(soup)

        assert result == []

    def test_handles_missing_attendees_gracefully(self):
        html = """
        <html><div id="okvPreview"><div class="previewData">
            <div>
                <span class="time">09:15 - 10:00</span>
                <span class="name">Yoga</span>
                <div class="donut-size" percentage="50 %"></div>
            </div>
        </div></div></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = CosmosClient._parse_today_upcoming_courses(soup)

        assert len(result) == 1
        assert result[0].participants == 0

    def test_handles_missing_donut_gracefully(self):
        html = """
        <html><div id="okvPreview"><div class="previewData">
            <div>
                <span class="time">09:15 - 10:00</span>
                <span class="name">Yoga</span>
                <span class="attendees">5 Teilnehmer</span>
            </div>
        </div></div></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = CosmosClient._parse_today_upcoming_courses(soup)

        assert len(result) == 1
        assert result[0].percentage == 0.0
