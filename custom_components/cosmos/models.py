"""Data models for Cosmos"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """User configuration"""

    username: str
    password: str
    mandant: str


@dataclass
class MandantData:
    """Session data from login"""

    login_token: str
    member_nr: str


@dataclass
class Course:
    """Course information from API"""

    nr: int
    course_name: str
    begin: str  # ISO datetime string
    end: str  # ISO datetime string
    booked: int
    online_book_max: int
    book_since: Optional[str] = None
    course_period_begin: Optional[str] = None
    course_period_end: Optional[str] = None
    course_price_single: Optional[str] = None
    course_nr: Optional[str] = None
    book_type: Optional[str] = None
    waitlist: int = 0
    max_anz: int = 0
    akt_anz: int = 0


@dataclass
class BookingOptions:
    """Options for booking a course"""

    course: str
    day: int  # 1=Monday, 7=Sunday
    hours: int  # 0-23
    minutes: int  # 0-59
