from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytz
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COUNTRY_TIMEZONES = {
    "Nigeria": "Africa/Lagos",
    "India": "Asia/Kolkata",
    "United states": "America/New_York",
    "United kingdom": "Europe/London",
    "Japan": "Asia/Tokyo",
    "Germany": "Europe/Berlin",
    "Singapore": "Asia/Singapore",
    "Bangladesh": "Asia/Dhaka",
}

async def convert_datetime(iso_input) -> str:
    """
    Accepts:
      - an ISO datetime string (e.g., '2025-07-12T09:08:47.435922+00:00')
      - a datetime.datetime object (naïve or timezone-aware)
    Returns a formatted UTC timestamp like 'July 12 25, 09:08 AM UTC+00'.
    """
    if isinstance(iso_input, str):
        dt = datetime.fromisoformat(iso_input)
    elif isinstance(iso_input, datetime):
        dt = iso_input
    else:
        raise TypeError("Input must be a string or datetime.datetime")

    month_name = dt.strftime("%B")
    day = dt.strftime("%d")
    year_suffix = dt.strftime("%y")
    time = dt.strftime("%I:%M %p")
    offset = dt.strftime("%z")

    utc_offset = f"UTC{offset[:3]}" if offset else "UTC"
    return f"{month_name} {day} {year_suffix}, {time} {utc_offset}"


async def format_utc_time_label(text: str) -> str:
    """
    Extracts a time and UTC offset from the input string and formats it as:
    'HH:MM AM UTC±HH (Today)' or '... (Tomorrow)'.
    """
    date_match = re.search(r'([A-Za-z]+ \d{1,2})', text)
    time_match = re.search(r'(\d{1,2}:\d{2} [AP]M) UTC([+-]\d{2})', text)

    if not date_match or not time_match:
        return "Invalid input format"

    date_str = f"{date_match.group(1)} {datetime.now(timezone.utc).year}"
    try:
        date_obj = datetime.strptime(date_str, "%B %d %Y").date()
    except ValueError:
        return "Invalid date in input"

    time_str = time_match.group(1)
    offset_str = time_match.group(2)
    hours_offset = int(offset_str)
    tzinfo = timezone(timedelta(hours=hours_offset))

    naive_datetime = datetime.combine(date_obj, datetime.strptime(time_str, "%I:%M %p").time())
    full_datetime = naive_datetime.replace(tzinfo=tzinfo)

    now_in_same_tz = datetime.now(tzinfo)
    label = "Today" if full_datetime.date() == now_in_same_tz.date() else "Tomorrow"

    # Format output
    formatted_time = full_datetime.strftime("%I:%M %p UTC") + offset_str
    return f"{formatted_time} ({label})"


async def convert_utc_to_country_time(utc_time_str: str, country_name: str) -> dict:
    """
    Converts a UTC ISO timestamp to the given country's local time, and also returns the current time
    in that country's timezone. Both are returned in ISO 8601 format.
    """
    utc_time = datetime.fromisoformat(utc_time_str)
    tz_name = COUNTRY_TIMEZONES.get(country_name)
    if not tz_name:
        raise ValueError(f"No timezone mapping found for country: {country_name}")

    zone = ZoneInfo(tz_name)

    local_time = utc_time.astimezone(zone)
    current_local_time = datetime.now(zone)

    return {
        "converted_time": local_time.isoformat(),
        "current_time": current_local_time.isoformat(),
    }