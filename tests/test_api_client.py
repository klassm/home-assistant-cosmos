"""Tests for API client"""

import re

import pytest

from custom_components.cosmos.api_client import CosmosClient
from custom_components.cosmos.const import BASE_URL
from custom_components.cosmos.exceptions import (
    AuthenticationError,
    BookingError,
)


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

    # Mock mycourses page with mandant data (no booked courses - now via API)
    html = """
    <html>
        <div id="jsvariable-data-mandantData"
             data-mandantdata='{"loginToken":"token123"}'></div>
        <div id="jsvariable-data-memberData"
              data-memberdata='{"nr":"12345"}'></div>
    </html>
    """
    mock_api.get(re.compile(rf"^{re.escape(mycourses_url)}\?"), status=200, body=html)

    async with CosmosClient(config) as client:
        await client.login()
        mandant_data = await client.get_mandant_data()

        assert mandant_data.login_token == "token123"
        assert mandant_data.member_nr == "12345"


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
async def test_get_workload(mock_api, config):
    """Test fetching workload via JSON API"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"
    workload_url = f"{BASE_URL}/workload"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)
    mock_api.get(
        re.compile(rf"^{re.escape(workload_url)}\?"),
        status=200,
        payload={
            "gym": 1,
            "name": "Cosmos Stadtbergen",
            "workload": "24,00 %",
            "numval": "24.00",
        },
    )

    async with CosmosClient(config) as client:
        await client.login()
        data = await client.get_workload()

        assert data["percentage"] == 24
        assert data["location"] == "Cosmos Stadtbergen"


@pytest.mark.asyncio
async def test_get_booked_courses(mock_api, config):
    """Test fetching booked courses via API"""
    login_url = f"{BASE_URL}/login"
    check_login_url = f"{BASE_URL}/check_login"

    mock_api.get(
        re.compile(rf"^{re.escape(login_url)}\?"),
        status=200,
        headers={"Set-Cookie": "PHPSESSID=test_session_id"},
    )
    mock_api.post(re.compile(rf"^{re.escape(check_login_url)}"), status=200)

    booked_data = {
        "booked_courses": [
            {
                "t601_lfnr": 161948,
                "course_name": "RückenFit",
                "begin": "2099-04-30T09:15:00",
                "end": "2099-04-30T10:00:00",
                "book_type": "single",
            },
            {
                "t601_lfnr": 154801,
                "course_name": "Bauch Beine Po",
                "begin": "2099-04-29T08:45:00",
                "end": "2099-04-29T09:45:00",
                "book_type": "single",
            },
            {
                "t601_lfnr": 999,
                "course_name": "Past Course",
                "begin": "2020-01-15T08:00:00",
                "end": "2020-01-15T09:00:00",
                "book_type": "single",
            },
        ],
        "count": 3,
    }
    mock_api.get(
        re.compile(rf"^{re.escape(BASE_URL)}/proxy\.php"),
        status=200,
        payload=booked_data,
    )

    async with CosmosClient(config) as client:
        await client.login()
        booked = await client.get_booked_courses(member_nr="12345", login_token="token")

        assert len(booked) == 2
        assert booked[0].name == "RückenFit"
        assert booked[0].date == "2099-04-30"
        assert booked[0].time == "09:15 - 10:00"
        assert booked[0].nr == 161948
        assert booked[1].name == "Bauch Beine Po"
        assert booked[1].date == "2099-04-29"
        assert booked[1].time == "08:45 - 09:45"
        assert booked[1].nr == 154801


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
            {
                "t601_lfnr": 1,
                "course_name": "Yoga",
                "begin": "2099-01-15T18:00:00",
                "end": "2099-01-15T19:00:00",
            },
            {
                "t601_lfnr": 2,
                "course_name": "Pilates",
                "begin": "2099-01-16T10:00:00",
                "end": "2099-01-16T11:00:00",
            },
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
        payload={
            "booked_courses": [
                {
                    "t601_lfnr": 999,
                    "course_name": "Zumba",
                    "begin": "2099-01-15T18:00:00",
                    "end": "2099-01-15T19:00:00",
                }
            ]
        },
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
