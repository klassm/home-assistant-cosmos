"""Tests for data models"""

import pytest

from custom_components.cosmos.models import (
    BookingOptions,
    Config,
    Course,
    MandantData,
)


def test_config_creation():
    """Test Config dataclass"""
    config = Config(username="user", password="pass", mandant="test_mandant")

    assert config.username == "user"
    assert config.password == "pass"
    assert config.mandant == "test_mandant"


def test_config_required_fields():
    """Test Config requires all fields"""
    with pytest.raises(TypeError):
        Config(username="user", password="pass")  # Missing mandant


def test_mandant_data_creation():
    """Test MandantData dataclass"""
    data = MandantData(login_token="token123", member_nr="12345")

    assert data.login_token == "token123"
    assert data.member_nr == "12345"


def test_mandant_data_required_fields():
    """Test MandantData requires all fields"""
    with pytest.raises(TypeError):
        MandantData(login_token="token")  # Missing member_nr


def test_course_creation(sample_course):
    """Test Course dataclass"""
    assert sample_course.nr == 1
    assert sample_course.course_name == "Yoga"
    assert sample_course.begin == "2024-01-15T18:00:00"
    assert sample_course.end == "2024-01-15T19:00:00"
    assert sample_course.booked == 0
    assert sample_course.online_book_max == 10


def test_course_optional_fields():
    """Test Course with optional fields"""
    course = Course(
        nr=2,
        course_name="Pilates",
        begin="2024-01-15T10:00:00",
        end="2024-01-15T11:00:00",
        booked=5,
        online_book_max=15,
    )

    assert course.nr == 2
    assert course.course_name == "Pilates"
    assert course.book_since is None
    assert course.course_period_begin is None
    assert course.waitlist == 0  # Default value
    assert course.max_anz == 0  # Default value


def test_course_all_fields():
    """Test Course with all fields populated"""
    course = Course(
        nr=3,
        course_name="Spinning",
        begin="2024-01-15T08:00:00",
        end="2024-01-15T09:00:00",
        booked=10,
        online_book_max=20,
        book_since="2024-01-01T00:00:00",
        course_period_begin="2024-01-01",
        course_period_end="2024-12-31",
        course_price_single="15.00",
        course_nr="SPIN101",
        book_type="online",
        waitlist=2,
        max_anz=25,
        akt_anz=10,
    )

    assert course.nr == 3
    assert course.course_name == "Spinning"
    assert course.book_since == "2024-01-01T00:00:00"
    assert course.course_price_single == "15.00"
    assert course.waitlist == 2
    assert course.max_anz == 25


def test_booking_options_creation():
    """Test BookingOptions dataclass"""
    options = BookingOptions(course="Yoga", day=1, hours=18, minutes=0)

    assert options.course == "Yoga"
    assert options.day == 1
    assert options.hours == 18
    assert options.minutes == 0


def test_booking_options_required_fields():
    """Test BookingOptions requires all fields"""
    with pytest.raises(TypeError):
        BookingOptions(course="Yoga")  # Missing day, hours, minutes


def test_booking_options_day_values():
    """Test BookingOptions day field (1=Monday, 7=Sunday)"""
    options_monday = BookingOptions(course="Yoga", day=1, hours=18, minutes=0)
    options_sunday = BookingOptions(course="Yoga", day=7, hours=18, minutes=0)

    assert options_monday.day == 1
    assert options_sunday.day == 7
