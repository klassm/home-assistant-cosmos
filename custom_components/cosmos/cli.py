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

    Fetches and displays the current gym load percentage from the member_home page.
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
        click.echo(result["percentage"])
    except CosmosError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
