"""Tests for booking operations"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import directly from submodules to avoid HA dependencies in __init__.py
from custom_components.cosmos.booking import (
    BookingReason,
    book_course,
    find_matching_courses,
    is_bookable,
    is_matching_course,
)
from custom_components.cosmos.exceptions import BookingError
from custom_components.cosmos.models import BookingOptions, Course


class TestIsBookable:
    """Tests for is_bookable function"""

    def test_is_bookable_true(self, sample_course):
        """Test if course is bookable"""
        assert is_bookable(sample_course) is True

    def test_is_bookable_no_online_booking(self, sample_course):
        """Test course with no online booking"""
        sample_course.online_book_max = 0
        assert is_bookable(sample_course) is False

    def test_is_bookable_with_future_book_since(self, sample_course):
        """Test course not yet bookable (book_since in future)"""
        future = datetime.now() + timedelta(days=7)
        sample_course.book_since = future.strftime("%Y-%m-%dT%H:%M:%S")
        assert is_bookable(sample_course) is False

    def test_is_bookable_with_past_book_since(self, sample_course):
        """Test course bookable (book_since in past)"""
        past = datetime.now() - timedelta(days=1)
        sample_course.book_since = past.strftime("%Y-%m-%dT%H:%M:%S")
        assert is_bookable(sample_course) is True

    def test_is_bookable_invalid_book_since_format(self, sample_course):
        """Test course with invalid book_since format defaults to bookable"""
        sample_course.book_since = "invalid-date"
        assert is_bookable(sample_course) is True


class TestIsMatchingCourse:
    """Tests for is_matching_course function"""

    def test_is_matching_course_true(self):
        """Test matching course"""
        future = datetime.now() + timedelta(days=7)
        begin = future.replace(hour=18, minute=0, second=0, microsecond=0)

        course = Course(
            nr=1,
            course_name="Yoga",
            begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
            end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            booked=0,
            online_book_max=10,
        )

        options = BookingOptions(
            course="Yoga", day=begin.isoweekday(), hours=18, minutes=0
        )

        assert is_matching_course(course, options) is True

    def test_is_matching_course_wrong_name(self):
        """Test course with wrong name"""
        future = datetime.now() + timedelta(days=7)
        begin = future.replace(hour=18, minute=0, second=0, microsecond=0)

        course = Course(
            nr=1,
            course_name="Pilates",
            begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
            end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            booked=0,
            online_book_max=10,
        )

        options = BookingOptions(
            course="Yoga", day=begin.isoweekday(), hours=18, minutes=0
        )

        assert is_matching_course(course, options) is False

    def test_is_matching_course_wrong_day(self):
        """Test course on wrong day"""
        future = datetime.now() + timedelta(days=7)
        begin = future.replace(hour=18, minute=0, second=0, microsecond=0)

        course = Course(
            nr=1,
            course_name="Yoga",
            begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
            end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            booked=0,
            online_book_max=10,
        )

        # Use a different day
        wrong_day = begin.isoweekday() % 7 + 1
        options = BookingOptions(course="Yoga", day=wrong_day, hours=18, minutes=0)

        assert is_matching_course(course, options) is False

    def test_is_matching_course_wrong_hour(self):
        """Test course at wrong hour"""
        future = datetime.now() + timedelta(days=7)
        begin = future.replace(hour=18, minute=0, second=0, microsecond=0)

        course = Course(
            nr=1,
            course_name="Yoga",
            begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
            end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            booked=0,
            online_book_max=10,
        )

        options = BookingOptions(
            course="Yoga", day=begin.isoweekday(), hours=19, minutes=0
        )

        assert is_matching_course(course, options) is False

    def test_is_matching_course_in_past(self):
        """Test course in the past"""
        past = datetime.now() - timedelta(days=1)
        begin = past.replace(hour=18, minute=0, second=0, microsecond=0)

        course = Course(
            nr=1,
            course_name="Yoga",
            begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
            end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            booked=0,
            online_book_max=10,
        )

        options = BookingOptions(
            course="Yoga", day=begin.isoweekday(), hours=18, minutes=0
        )

        assert is_matching_course(course, options) is False

    def test_is_matching_course_invalid_begin_format(self, sample_course):
        """Test course with invalid begin format"""
        sample_course.begin = "invalid-date"

        options = BookingOptions(course="Yoga", day=1, hours=18, minutes=0)

        assert is_matching_course(sample_course, options) is False


class TestFindMatchingCourses:
    """Tests for find_matching_courses function"""

    def test_find_matching_courses_found(self):
        """Test finding matching courses"""
        future = datetime.now() + timedelta(days=7)
        begin = future.replace(hour=18, minute=0, second=0, microsecond=0)

        course = Course(
            nr=1,
            course_name="Yoga",
            begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
            end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            booked=0,
            online_book_max=10,
        )

        courses = [course]
        options = BookingOptions(
            course="Yoga", day=begin.isoweekday(), hours=18, minutes=0
        )

        bookable, not_bookable = find_matching_courses(courses, options)

        assert len(bookable) == 1
        assert len(not_bookable) == 0
        assert bookable[0].course_name == "Yoga"

    def test_find_matching_courses_no_match(self):
        """Test finding courses with no match"""
        future = datetime.now() + timedelta(days=7)
        begin = future.replace(hour=18, minute=0, second=0, microsecond=0)

        course = Course(
            nr=1,
            course_name="Yoga",
            begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
            end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            booked=0,
            online_book_max=10,
        )

        courses = [course]
        options = BookingOptions(
            course="Pilates", day=begin.isoweekday(), hours=18, minutes=0
        )

        bookable, not_bookable = find_matching_courses(courses, options)

        assert len(bookable) == 0
        assert len(not_bookable) == 0

    def test_find_matching_courses_not_bookable_yet(self):
        """Test finding matching courses that are not yet bookable"""
        future_date = datetime.now() + timedelta(days=14)
        begin = future_date.replace(hour=18, minute=0, second=0, microsecond=0)
        book_since_future = datetime.now() + timedelta(days=7)

        course = Course(
            nr=1,
            course_name="Yoga",
            begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
            end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            booked=0,
            online_book_max=10,
            book_since=book_since_future.strftime("%Y-%m-%dT%H:%M:%S"),
        )

        courses = [course]
        options = BookingOptions(
            course="Yoga", day=begin.isoweekday(), hours=18, minutes=0
        )

        bookable, not_bookable = find_matching_courses(courses, options)

        assert len(bookable) == 0
        assert len(not_bookable) == 1


class TestBookCourse:
    """Tests for book_course async function"""

    @pytest.mark.asyncio
    async def test_book_course_success(self):
        """Test successful booking"""
        future = datetime.now() + timedelta(days=7)
        begin = future.replace(hour=18, minute=0, second=0, microsecond=0)

        client = MagicMock()
        client.get_mandant_data = AsyncMock(
            return_value=MagicMock(login_token="token", member_nr="12345")
        )
        client.find_courses = AsyncMock(
            return_value=[
                Course(
                    nr=1,
                    course_name="Yoga",
                    begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
                    end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                    booked=0,
                    online_book_max=10,
                    course_nr=101,
                    course_period_begin="2024-01-01",
                    course_period_end="2024-12-31",
                    course_price_single="10.00",
                    book_type="online",
                    waitlist=0,
                    max_anz=20,
                    akt_anz=15,
                )
            ]
        )
        client.is_already_booked = AsyncMock(return_value=False)
        client.book_course = AsyncMock(return_value="Successfully booked")

        options = BookingOptions(
            course="Yoga", day=begin.isoweekday(), hours=18, minutes=0
        )
        result = await book_course(client, options)

        assert result["success"] is True
        assert result["reason"] == BookingReason.NEWLY_BOOKED
        assert "Successfully booked" in result["message"]

    @pytest.mark.asyncio
    async def test_book_course_not_found(self):
        """Test booking when course not found"""
        client = MagicMock()
        client.get_mandant_data = AsyncMock(
            return_value=MagicMock(login_token="token", member_nr="12345")
        )
        client.find_courses = AsyncMock(return_value=[])

        options = BookingOptions(course="NonExistent", day=1, hours=18, minutes=0)
        result = await book_course(client, options)

        assert result["success"] is False
        assert result["reason"] == BookingReason.NOT_FOUND
        assert "No matching course" in result["message"]

    @pytest.mark.asyncio
    async def test_book_course_already_booked(self):
        """Test booking when already booked"""
        future = datetime.now() + timedelta(days=7)
        begin = future.replace(hour=18, minute=0, second=0, microsecond=0)

        client = MagicMock()
        client.get_mandant_data = AsyncMock(
            return_value=MagicMock(login_token="token", member_nr="12345")
        )
        client.find_courses = AsyncMock(
            return_value=[
                Course(
                    nr=1,
                    course_name="Yoga",
                    begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
                    end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                    booked=0,
                    online_book_max=10,
                    course_nr=101,
                    course_period_begin="2024-01-01",
                    course_period_end="2024-12-31",
                    course_price_single="10.00",
                    book_type="online",
                    waitlist=0,
                    max_anz=20,
                    akt_anz=15,
                )
            ]
        )
        client.is_already_booked = AsyncMock(return_value=True)

        options = BookingOptions(
            course="Yoga", day=begin.isoweekday(), hours=18, minutes=0
        )
        result = await book_course(client, options)

        assert result["success"] is True
        assert result["reason"] == BookingReason.ALREADY_BOOKED
        assert "already booked" in result["message"]

    @pytest.mark.asyncio
    async def test_book_course_full(self):
        """Test booking when course is full"""
        future = datetime.now() + timedelta(days=7)
        begin = future.replace(hour=18, minute=0, second=0, microsecond=0)

        client = MagicMock()
        client.get_mandant_data = AsyncMock(
            return_value=MagicMock(login_token="token", member_nr="12345")
        )
        client.find_courses = AsyncMock(
            return_value=[
                Course(
                    nr=1,
                    course_name="Yoga",
                    begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
                    end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                    booked=0,
                    online_book_max=10,
                    course_nr=101,
                    course_period_begin="2024-01-01",
                    course_period_end="2024-12-31",
                    course_price_single="10.00",
                    book_type="online",
                    waitlist=0,
                    max_anz=20,
                    akt_anz=20,  # Full!
                )
            ]
        )
        client.is_already_booked = AsyncMock(return_value=False)

        options = BookingOptions(
            course="Yoga", day=begin.isoweekday(), hours=18, minutes=0
        )
        result = await book_course(client, options)

        assert result["success"] is False
        assert result["reason"] == BookingReason.FULL
        assert "course is full" in result["message"]

    @pytest.mark.asyncio
    async def test_book_course_error(self):
        """Test booking when client.book_course raises BookingError"""
        future = datetime.now() + timedelta(days=7)
        begin = future.replace(hour=18, minute=0, second=0, microsecond=0)

        client = MagicMock()
        client.get_mandant_data = AsyncMock(
            return_value=MagicMock(login_token="token", member_nr="12345")
        )
        client.find_courses = AsyncMock(
            return_value=[
                Course(
                    nr=1,
                    course_name="Yoga",
                    begin=begin.strftime("%Y-%m-%dT%H:%M:%S"),
                    end=(begin + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                    booked=0,
                    online_book_max=10,
                    course_nr=101,
                    course_period_begin="2024-01-01",
                    course_period_end="2024-12-31",
                    course_price_single="10.00",
                    book_type="online",
                    waitlist=0,
                    max_anz=20,
                    akt_anz=10,
                )
            ]
        )
        client.is_already_booked = AsyncMock(return_value=False)
        client.book_course = AsyncMock(side_effect=BookingError("Network error"))

        options = BookingOptions(
            course="Yoga", day=begin.isoweekday(), hours=18, minutes=0
        )
        result = await book_course(client, options)

        assert result["success"] is False
        assert result["reason"] == BookingReason.ERROR
        assert "Network error" in result["message"]
