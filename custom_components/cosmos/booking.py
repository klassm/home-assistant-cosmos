"""High-level booking operations"""

from datetime import datetime
from enum import Enum


class BookingReason(str, Enum):
    """Reason for the booking outcome."""

    ALREADY_BOOKED = "already_booked"
    NEWLY_BOOKED = "newly_booked"
    FULL = "full"
    ERROR = "error"
    NOT_FOUND = "not_found"


from .api_client import CosmosClient
from .exceptions import BookingError
from .models import BookingOptions, Course


def is_matching_course(course: Course, options: BookingOptions) -> bool:
    """Check if course matches booking options.

    Matches by:
    - Course name (exact match)
    - Day of week
    - Hour and minute of start time
    - Must be in the future

    Args:
        course: Course to check
        options: Booking criteria

    Returns:
        True if course matches
    """
    # Parse begin datetime (format: yyyy-MM-dd'T'HH:mm:ss)
    try:
        begin_dt = datetime.strptime(course.begin, "%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError):
        return False

    now = datetime.now()

    # Check all criteria
    return (
        begin_dt.isoweekday() == options.day  # Monday=1, Sunday=7
        and begin_dt.hour == options.hours
        and begin_dt.minute == options.minutes
        and course.course_name == options.course
        and begin_dt > now
    )


def is_bookable(course: Course) -> bool:
    """Check if course can be booked now.

    A course is bookable if:
    - book_since is in the past or not set
    - online_book_max > 0

    Args:
        course: Course to check

    Returns:
        True if bookable
    """
    if course.online_book_max <= 0:
        return False

    if not course.book_since:
        return True

    try:
        book_since_dt = datetime.strptime(course.book_since, "%Y-%m-%dT%H:%M:%S")
        now = datetime.now()
        return book_since_dt <= now
    except (ValueError, TypeError):
        return True  # If we can't parse, assume bookable


def find_matching_courses(
    courses: list[Course],
    options: BookingOptions,
) -> tuple[list[Course], list[Course]]:
    """Filter courses into bookable and not-yet-bookable.

    Args:
        courses: All available courses
        options: Booking criteria

    Returns:
        Tuple of (bookable_courses, not_bookable_courses)
    """
    matching = [c for c in courses if is_matching_course(c, options)]
    bookable = [c for c in matching if is_bookable(c)]
    not_bookable = [c for c in matching if not is_bookable(c)]

    return bookable, not_bookable


async def book_course(
    client: CosmosClient,
    options: BookingOptions,
) -> dict:
    """Book the first matching course.

    Flow:
    1. Get mandant data (login token, member nr)
    2. Find courses matching options
    3. Filter to bookable courses
    4. Book the first bookable course and return immediately

    Args:
        client: Authenticated API client
        options: Booking criteria

    Returns:
        Dict with booking result containing:
        - success: True for ALREADY_BOOKED / NEWLY_BOOKED, False otherwise
        - reason: BookingReason value
        - message: Human-readable description
        - course, day, time: Booking criteria echo
    """
    # Step 1: Get mandant data
    mandant_data = await client.get_mandant_data()

    # Step 2: Find all courses
    courses = await client.find_courses(
        member_nr=mandant_data.member_nr,
        login_token=mandant_data.login_token,
    )

    # Step 3: Filter matching courses
    bookable, not_bookable = find_matching_courses(courses, options)

    # Log not-yet-bookable courses
    if not_bookable and not bookable:
        messages = [
            f"  * {c.course_name} {c.begin} bookable from {c.book_since}"
            for c in not_bookable
        ]
        print("Found matching courses, which are not bookable:\n" + "\n".join(messages))

    if not bookable:
        return {
            "success": False,
            "reason": BookingReason.NOT_FOUND,
            "message": (
                f"No matching course found: '{options.course}' "
                f"day={options.day} time={options.hours:02d}:{options.minutes:02d}"
            ),
            "course": options.course,
            "day": options.day,
            "time": f"{options.hours:02d}:{options.minutes:02d}",
        }

    # Step 4: Book the first bookable course
    course = bookable[0]
    prefix = f"{course.course_name} {course.begin}"

    # Check if already booked
    is_booked = await client.is_already_booked(
        course=course,
        member_nr=mandant_data.member_nr,
        login_token=mandant_data.login_token,
    )

    if is_booked:
        return {
            "success": True,
            "reason": BookingReason.ALREADY_BOOKED,
            "message": f"{prefix}: already booked",
            "course": options.course,
            "day": options.day,
            "time": f"{options.hours:02d}:{options.minutes:02d}",
        }

    # Check if full
    if course.akt_anz >= course.max_anz:
        return {
            "success": False,
            "reason": BookingReason.FULL,
            "message": f"{prefix}: course is full",
            "course": options.course,
            "day": options.day,
            "time": f"{options.hours:02d}:{options.minutes:02d}",
        }

    # Try to book
    try:
        result = await client.book_course(course)
        return {
            "success": True,
            "reason": BookingReason.NEWLY_BOOKED,
            "message": f"{prefix}: {result}",
            "course": options.course,
            "day": options.day,
            "time": f"{options.hours:02d}:{options.minutes:02d}",
        }
    except BookingError as e:
        return {
            "success": False,
            "reason": BookingReason.ERROR,
            "message": f"{prefix}: {e}",
            "course": options.course,
            "day": options.day,
            "time": f"{options.hours:02d}:{options.minutes:02d}",
        }
