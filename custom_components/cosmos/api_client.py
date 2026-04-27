"""Async API client for Cosmos portal"""

import json
import logging
from typing import Any, Optional
from urllib.parse import quote, urlencode

import aiohttp
from bs4 import BeautifulSoup

from .const import BASE_URL, PROXY_BASE_URL
from .exceptions import AuthenticationError, BookingError
from .models import BookedCourse, Config, Course, MandantData, TodayCourse

_LOGGER = logging.getLogger(__name__)


class CosmosClient:
    """Async client for Cosmos portal.

    Use as async context manager:
        async with CosmosClient(config) as client:
            await client.login()
            ...
    """

    def __init__(self, config: Config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.session_id: Optional[str] = None  # Stored for logging/debugging

    async def __aenter__(self) -> "CosmosClient":
        """Enter async context - create session with cookie jar."""
        # Create session with trust_env=True for proxy support
        # aiohttp automatically manages cookies in the session's cookie jar
        # Set cookie_jar with quote_cookie=False to handle German portal cookies
        jar = aiohttp.CookieJar(
            unsafe=True
        )  # unsafe=True allows cookies from any domain
        self.session = aiohttp.ClientSession(trust_env=True, cookie_jar=jar)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Exit async context - close session."""
        if self.session:
            await self.session.close()
            self.session = None

    def _require_session(self) -> aiohttp.ClientSession:
        """Ensure session is available."""
        if not self.session:
            raise RuntimeError("Use async context manager")
        return self.session

    async def login(self) -> str:
        """Perform login and return session ID.

        Port of TypeScript login.ts doLogin()

        Flow (matching TypeScript exactly):
        1. GET login page to establish session (cookies auto-stored in jar)
        2. POST credentials to check_login (cookies auto-sent from jar)
        3. Verify login success

        Returns:
            PHPSESSID session cookie value
        """
        session = self._require_session()
        login_url = f"{BASE_URL}/login"
        params = {"mandant": self.config.mandant}

        # Step 1: GET login page to establish session
        # aiohttp stores cookies from Set-Cookie in the session's cookie jar
        async with session.get(login_url, params=params) as resp:
            if resp.status != 200:
                raise AuthenticationError(f"Login page failed: {resp.status}")

            # Extract PHPSESSID for logging and return value
            for cookie in session.cookie_jar:
                if cookie.key == "PHPSESSID":
                    self.session_id = cookie.value
                    break

            if not self.session_id:
                raise AuthenticationError("No session cookie from login page")

        # Step 2: POST credentials
        # aiohttp automatically sends cookies from the jar with the request
        # Match TypeScript: POST to check_login with mandant and id params
        check_login_url = f"{BASE_URL}/check_login"
        check_params = {"mandant": self.config.mandant, "id": self.session_id}
        form_data = {
            "username": self.config.username,
            "password": self.config.password,
        }

        async with session.post(
            check_login_url,
            params=check_params,
            data=form_data,
        ) as resp:
            text = await resp.text()

            # Check for authentication failure
            if "Anmeldung fehlgeschlagen" in text:
                raise AuthenticationError("Invalid username or password")

        return self.session_id

    async def get_mandant_data(self) -> MandantData:
        """Get login token and member number from mycourses page.

        Port of TypeScript book.ts getMandantData()

        Cookies are automatically sent by aiohttp from the session's cookie jar.

        Returns:
            MandantData with loginToken and memberNr
        """
        session = self._require_session()

        if not self.session_id:
            raise AuthenticationError("Not logged in")

        url = f"{BASE_URL}/mycourses"
        # TypeScript uses mandant and id params
        # Cookies are sent automatically from the jar
        params = {"mandant": self.config.mandant, "id": self.session_id}

        async with session.get(url, params=params) as resp:
            html = await resp.text()

        # Parse HTML and extract data attributes
        soup = BeautifulSoup(html, "html.parser")

        # Find element with data-mandantData
        mandant_element = soup.find(id="jsvariable-data-mandantData")
        if not mandant_element:
            raise BookingError("Cannot find mandantData element in page")

        mandant_data_attr = mandant_element.get("data-mandantdata")
        if not mandant_data_attr:
            raise BookingError("Cannot find data-mandantData attribute")

        mandant_json = json.loads(mandant_data_attr)

        # Find element with data-memberData
        member_element = soup.find(id="jsvariable-data-memberData")
        if not member_element:
            raise BookingError("Cannot find memberData element in page")

        member_data_attr = member_element.get("data-memberdata")
        if not member_data_attr:
            raise BookingError("Cannot find data-memberData attribute")

        member_json = json.loads(member_data_attr)

        login_token = mandant_json.get("loginToken")
        member_nr = member_json.get("nr")

        if not login_token:
            raise BookingError("Cannot extract loginToken from mandantData")
        if not member_nr:
            raise BookingError("Cannot extract memberNr from memberData")

        booked = self._parse_booked_courses(soup)

        return MandantData(login_token=login_token, member_nr=str(member_nr)), booked

    @staticmethod
    def _parse_booked_courses(soup: BeautifulSoup) -> list[BookedCourse]:
        """Parse future bookings from the mycourses page."""
        future = soup.find("div", class_="futureBookings")
        if not future:
            return []

        rows = future.find_all("tr", class_="swipeable")
        result: list[BookedCourse] = []
        for row in rows:
            try:
                name_el = row.find("span", class_="courseName")
                tds = row.find_all("td")
                if not name_el or len(tds) < 3:
                    continue

                name = name_el.get_text(strip=True)
                date = ""
                time_ = ""
                for td in tds:
                    cls = td.get("class", [])
                    if "showformediumup" in cls and "storno" not in cls:
                        date = td.get_text(strip=True)
                    if not time_ and td.get_text(strip=True) and " - " in td.get_text():
                        time_ = td.get_text(strip=True)

                result.append(BookedCourse(name=name, date=date, time=time_))
            except Exception:
                continue

        return result

    async def get_load(self) -> dict:
        """Get current gym load and today's courses from member_home page.

        Returns:
            dict with keys:
                - percentage: int (0-100)
                - time: str (HH:MM format)
                - location: str (gym name)
                - today_upcoming_courses: list[TodayCourse]

        Raises:
            BookingError: If load data cannot be extracted
        """
        session = self._require_session()

        # Early exit: verify logged in (Law of Early Exit)
        if not self.session_id:
            raise AuthenticationError("Not logged in")

        url = f"{BASE_URL}/member_home"
        params = {"mandant": self.config.mandant, "id": self.session_id}

        async with session.get(url, params=params) as resp:
            html = await resp.text()

        # Parse HTML to extract load
        soup = BeautifulSoup(html, "html.parser")

        # Find the chartContainer div
        chart = soup.find("div", class_="chartContainer")
        if not chart:
            raise BookingError("Cannot find load chart on page")

        # Find the donut chart div with percentage attribute
        donut = chart.find("div", class_="donut-size")
        if not donut:
            raise BookingError("Cannot find load percentage")

        # Extract percentage (format: "13,00 %")
        percentage_str = donut.get("percentage", "")
        if not percentage_str:
            raise BookingError("Cannot find percentage attribute")

        # Parse percentage: "13,00 %" -> 13
        try:
            # Remove % and spaces, replace comma with dot for parsing
            percentage_clean = percentage_str.replace("%", "").replace(",", ".").strip()
            percentage = int(float(percentage_clean))
        except (ValueError, AttributeError):
            raise BookingError(f"Invalid percentage format: {percentage_str}")

        # Extract location name
        label = donut.find("h5", class_="chartlabel")
        location = label.text.strip() if label else "Unknown"

        # Extract time
        time_elem = donut.find("h5", class_="time")
        time_str = time_elem.text.strip() if time_elem else ""

        # Extract today's courses from okvPreview section
        today_upcoming_courses = self._parse_today_upcoming_courses(soup)

        return {
            "percentage": percentage,
            "time": time_str,
            "location": location,
            "today_upcoming_courses": today_upcoming_courses,
        }

    @staticmethod
    def _parse_today_upcoming_courses(soup: BeautifulSoup) -> list[TodayCourse]:
        """Parse today's courses from the okvPreview section of the page.

        Args:
            soup: Parsed HTML of the member_home page

        Returns:
            List of TodayCourse objects (empty if section not found)
        """
        preview = soup.find("div", id="okvPreview")
        if not preview:
            return []

        preview_data = preview.find("div", class_="previewData")
        if not preview_data:
            return []

        courses: list[TodayCourse] = []
        for course_div in preview_data.find_all("div", recursive=False):
            # Extract course name
            name_elem = course_div.find("span", class_="name")
            if not name_elem:
                continue
            course_name = name_elem.get_text(strip=True)

            # Extract time range (format: "HH:MM - HH:MM")
            time_elem = course_div.find("span", class_="time")
            if not time_elem:
                continue
            time_text = time_elem.get_text(strip=True)

            # Parse start and end time
            try:
                parts = time_text.split("-")
                start_time = parts[0].strip()
                end_time = parts[1].strip()
            except (IndexError, ValueError):
                continue

            # Extract participants (format: "11 Teilnehmer")
            attendees_elem = course_div.find("span", class_="attendees")
            participants = 0
            if attendees_elem:
                attendees_text = attendees_elem.get_text(strip=True)
                try:
                    participants = int(attendees_text.split()[0])
                except (ValueError, IndexError):
                    pass

            # Extract percentage from donut-size div (format: "34 %")
            donut = course_div.find("div", class_="donut-size")
            percentage = 0.0
            if donut:
                pct_str = donut.get("percentage", "")
                if pct_str:
                    try:
                        pct_clean = pct_str.replace("%", "").replace(",", ".").strip()
                        percentage = float(pct_clean) / 100.0
                    except (ValueError, AttributeError):
                        pass

            courses.append(
                TodayCourse(
                    course=course_name,
                    participants=participants,
                    percentage=percentage,
                    start_time=start_time,
                    end_time=end_time,
                )
            )

        return courses

    def _build_proxy_url(self, path: str, params: dict[str, Any]) -> str:
        """Build proxy URL for API calls.

        The proxy.php forwards requests to the internal API server.
        """
        # Build the internal URL
        internal_url = f"https://85.214.169.244{path}?{urlencode(params)}"

        # Build proxy URL with URL-encoded internal URL
        # proxy.php?port=23660&param=<encoded_url>
        return f"{PROXY_BASE_URL}?port=23660&param={quote(internal_url, safe='')}"

    async def find_courses(
        self,
        member_nr: str,
        login_token: str,
    ) -> list[Course]:
        """Get available courses from courseplan API.

        Port of TypeScript book.ts findCourses()

        Args:
            member_nr: Member number from mandant data
            login_token: Login token from mandant data

        Returns:
            List of Course objects
        """
        from datetime import datetime, timedelta

        session = self._require_session()

        # Calculate date range (now to +2 weeks)
        now = datetime.now()
        end = now + timedelta(weeks=2)

        start_date = now.strftime("%Y-%m-%d")
        end_date = end.strftime("%Y-%m-%d")

        # Build proxy URL - match TypeScript params exactly (includes id param)
        params = {
            "since": start_date,
            "until": end_date,
            "stud_nr": "1",
            "member_nr": member_nr,
            "courseonlinegroup_nr": "0",
            "aidoomembernr": member_nr,
            "loginToken": login_token,
            "id": self.session_id,
        }
        proxy_url = self._build_proxy_url("/v0001/courseplan", params)

        # Make request with SSL verification disabled (like TypeScript)
        # Cookies are sent automatically from the jar
        async with session.get(proxy_url, ssl=False) as resp:
            # Get the response as text first to see what we're getting
            text = await resp.text()

            # Then try to parse as JSON
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                _LOGGER.error(f"Failed to parse response as JSON: {e}")
                _LOGGER.error(f"Full response text: {text}")
                raise

        courses_data = data.get("courses", [])
        courses = []

        for item in courses_data:
            course = Course(
                nr=item.get("nr", 0),
                course_name=item.get("course_name", ""),
                begin=item.get("begin", ""),
                end=item.get("end", ""),
                booked=item.get("booked", 0),
                online_book_max=item.get("online_book_max", 0),
                book_since=item.get("book_since"),
                course_period_begin=item.get("course_period_begin"),
                course_period_end=item.get("course_period_end"),
                course_price_single=item.get("course_price_single"),
                course_nr=item.get("course_nr"),
                book_type=item.get("book_type"),
                waitlist=item.get("waitlist", 0),
                max_anz=item.get("max_anz", 0),
                akt_anz=item.get("akt_anz", 0),
            )
            courses.append(course)

        return courses

    async def is_already_booked(
        self,
        course: Course,
        member_nr: str,
        login_token: str,
    ) -> bool:
        """Check if course is already booked.

        Port of TypeScript book.ts isAlreadyBooked()

        Args:
            course: Course to check
            member_nr: Member number
            login_token: Login token

        Returns:
            True if already booked
        """
        session = self._require_session()

        # Match TypeScript params exactly (includes id param)
        params = {
            "member_nr": member_nr,
            "offset": "0",
            "limit": "1000",
            "menueOnlineGroup": "-1",
            "loginToken": login_token,
            "aidoomembernr": member_nr,
            "id": self.session_id,
        }
        proxy_url = self._build_proxy_url("/v0001/booked_courses", params)

        async with session.get(proxy_url, ssl=False) as resp:
            # Get the response as text first (proxy returns HTML with embedded JSON)
            text = await resp.text()

            # Then parse as JSON
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                _LOGGER.error(f"Failed to parse booked_courses response as JSON: {e}")
                _LOGGER.error(f"Full response text: {text}")
                raise

        booked_courses = data.get("booked_courses", [])

        for booked in booked_courses:
            if booked.get("t601_lfnr") == course.nr:
                return True

        return False

    async def book_course(self, course: Course) -> str:
        """Book a course.

        Port of TypeScript book.ts bookOnAidoo()

        Args:
            course: Course to book

        Returns:
            Success message
        """
        session = self._require_session()

        if not self.session_id:
            raise AuthenticationError("Not logged in")

        # Prepare course data
        course_data = [
            {
                "coursePeriodBegin": course.course_period_begin,
                "coursePeriodEnd": course.course_period_end,
                "courseNr": course.course_nr,
                "coursePrice": course.course_price_single,
                "courseSendPrice": course.course_price_single,
                "courseBegin": f"{course.begin}+02:00",
                "courseEnd": f"{course.end}+02:00",
                "courseId": str(course.nr),
                "courseBookType": course.book_type,
                "courseName": course.course_name,
                "isWaitList": str(course.waitlist),
            }
        ]

        # Step 1: POST to /newmember/agb
        # Match TypeScript: includes id param
        # Match TypeScript postFormUrlEncoded: explicit Content-Type with charset
        agb_url = f"{BASE_URL}/newmember/agb"
        agb_params = {
            "mandant": self.config.mandant,
            "currentModule": "okv_begin",
            "id": self.session_id,
        }
        agb_data = {"courseDataField": json.dumps(course_data)}
        agb_headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        }

        async with session.post(
            agb_url, params=agb_params, data=agb_data, headers=agb_headers
        ) as resp:
            text = await resp.text()

            if resp.status != 200:
                raise BookingError(f"Failed to book course: HTTP {resp.status}")

            # Check response for various conditions
            # First check for successful booking confirmation page
            if "Buchung jetzt abschließen" in text or "memberagbaccepted" in text:
                # This is the expected booking confirmation page
                pass
            elif "AGB akzeptieren" in text:
                # Expected - AGB page returned, continue to step 2
                pass
            elif (
                "ist voll" in text
                or "vollständig gebucht" in text
                or "keine Plätze" in text
            ):
                raise BookingError("Course is full")
            elif "bereits gebucht" in text or "schon gebucht" in text:
                raise BookingError("Course is already booked")
            elif "fehler" in text.lower() or "error" in text.lower():
                raise BookingError("Booking failed - server error")
            else:
                # Unknown response - log for debugging
                _LOGGER.error(f"Unexpected booking response: {text[:1000]}")
                raise BookingError(
                    f"Could not book course - unexpected response. "
                    f"Preview: {text[:200]}"
                )

        # Step 2: POST to /memberagbaccepted
        # Match TypeScript: includes id param
        # Match TypeScript postFormUrlEncoded: explicit Content-Type with charset
        accepted_url = f"{BASE_URL}/memberagbaccepted"
        accepted_params = {
            "currentModule": "okv",
            "mandant": self.config.mandant,
            "id": self.session_id,
        }
        accepted_data = {
            "currentModule": "okv",
            "mandant": self.config.mandant,
            "id": self.session_id,
        }
        accepted_headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        }

        async with session.post(
            accepted_url,
            params=accepted_params,
            data=accepted_data,
            headers=accepted_headers,
        ) as resp:
            text = await resp.text()

            if "Vielen Dank und wir freuen uns auf deinen Besuch!" in text:
                return "Successfully booked"

            raise BookingError("Booking failed: missing success message")
