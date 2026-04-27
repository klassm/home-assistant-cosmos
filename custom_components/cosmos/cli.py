#!/usr/bin/env python3
"""Click-based CLI for Cosmos booking."""

import asyncio
import sys

import click

from .api_client import CosmosClient
from .booking import BookingOptions, book_course
from .config import load_config_from_env
from .exceptions import CosmosError
from .utils import parse_weekday


@click.group()
def cli() -> None:
    """Cosmos Booking CLI."""
    pass


@cli.command()
@click.option("--course", required=True, help='Course name (e.g., "Yoga")')
@click.option("--day", required=True, help="Day (1-7, Mo-So, or Mon-Sun)")
@click.option("--time", required=True, help="Time in HH:MM format")
def book(course: str, day: str, time: str) -> None:
    """Book a course at Cosmos.

    Example:
        cosmos book --course "Yoga" --day Mon --time "18:00"
        cosmos book --course "Yoga" --day Mo --time "18:00"
        cosmos book --course "Yoga" --day 1 --time "18:00"
    """
    # Early exit: validate time format (Law of Early Exit)
    try:
        hours, minutes = map(int, time.split(":"))
    except ValueError:
        click.echo(f"Invalid time format: {time}. Use HH:MM format.", err=True)
        raise SystemExit(1)

    # Parse weekday (Parse at boundary - Law of Parse Don't Validate)
    try:
        day_num = parse_weekday(day)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)

    # Validate hours and minutes
    if hours < 0 or hours > 23:
        click.echo(f"Invalid hours: {hours}. Must be 0-23.", err=True)
        raise SystemExit(1)
    if minutes < 0 or minutes > 59:
        click.echo(f"Invalid minutes: {minutes}. Must be 0-59.", err=True)
        raise SystemExit(1)

    # Load config from .env (Parse at boundary - Law of Parse Don't Validate)
    try:
        config = load_config_from_env()
    except CosmosError as e:
        click.echo(f"Configuration error: {e}", err=True)
        raise SystemExit(1)

    # Run async booking (Atomic Predictability - isolated async function)
    async def run_booking() -> dict:
        async with CosmosClient(config) as client:
            await client.login()

            options = BookingOptions(
                course=course,
                day=day_num,
                hours=hours,
                minutes=minutes,
            )

            return await book_course(client, options)

    try:
        result = asyncio.run(run_booking())
        click.echo(result.get("message", "Booking successful"))
    except CosmosError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
def load() -> None:
    """Display current gym load.

    Fetches and displays the current gym load percentage from the workload API.
    """
    # Load config from .env (Parse at boundary - Law of Parse Don't Validate)
    try:
        config = load_config_from_env()
    except CosmosError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    # Run async load fetch (Atomic Predictability - isolated async function)
    async def run_get_load() -> dict:
        async with CosmosClient(config) as client:
            await client.login()
            return await client.get_workload()

    try:
        result = asyncio.run(run_get_load())
        click.echo(f"{result['percentage']}% - {result['location']}")
    except CosmosError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def booked() -> None:
    """Display booked courses.

    Fetches and displays future booked courses from the API.
    """
    try:
        config = load_config_from_env()
    except CosmosError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    async def run_get_booked() -> list:
        async with CosmosClient(config) as client:
            await client.login()
            mandant_data = await client.get_mandant_data()
            return await client.get_booked_courses(
                mandant_data.member_nr, mandant_data.login_token
            )

    try:
        courses = asyncio.run(run_get_booked())
        if not courses:
            click.echo("No booked courses.")
        else:
            for course in courses:
                click.echo(f"{course.date}  {course.time}  {course.name}")
    except CosmosError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def upcoming() -> None:
    """Display today's upcoming courses.

    Fetches and displays today's courses that haven't ended yet.
    """
    try:
        config = load_config_from_env()
    except CosmosError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    async def run_get_upcoming() -> list:
        async with CosmosClient(config) as client:
            await client.login()
            mandant_data = await client.get_mandant_data()
            return await client.get_today_upcoming_courses(
                mandant_data.member_nr, mandant_data.login_token
            )

    try:
        courses = asyncio.run(run_get_upcoming())
        if not courses:
            click.echo("No upcoming courses today.")
        else:
            for course in courses:
                click.echo(
                    f"{course.start_time}-{course.end_time}  "
                    f"{course.course}  "
                    f"{course.participants} ({int(course.percentage * 100)}%)"
                )
    except CosmosError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def participants() -> None:
    """Display current course participants.

    Shows today's active courses and their current participant count.
    """
    try:
        config = load_config_from_env()
    except CosmosError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    async def run_get_participants() -> list:
        async with CosmosClient(config) as client:
            await client.login()
            mandant_data = await client.get_mandant_data()
            return await client.get_today_upcoming_courses(
                mandant_data.member_nr, mandant_data.login_token
            )

    try:
        courses = asyncio.run(run_get_participants())
        active = [c for c in courses if c.current_participants > 0]
        if not active:
            click.echo("No active courses right now.")
        else:
            total = 0
            for course in active:
                click.echo(
                    f"{course.start_time}-{course.end_time}  "
                    f"{course.course}  "
                    f"{course.current_participants}/{course.participants}"
                )
                total += course.current_participants
            click.echo(f"Total: {total}")
    except CosmosError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
