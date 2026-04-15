"""
Agent World Context Service — ground AI agents in reality.

One call per session. Returns everything an agent needs to know about
the current state of the world: time, timezone, DST, market hours,
holidays, business hours, day type, quarter.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Market schedules (exchange → timezone, open/close hours)
# ---------------------------------------------------------------------------
EXCHANGES = {
    "NYSE": {"tz": "America/New_York", "open": (9, 30), "close": (16, 0), "name": "New York Stock Exchange"},
    "NASDAQ": {"tz": "America/New_York", "open": (9, 30), "close": (16, 0), "name": "NASDAQ"},
    "LSE": {"tz": "Europe/London", "open": (8, 0), "close": (16, 30), "name": "London Stock Exchange"},
    "TSE": {"tz": "Asia/Tokyo", "open": (9, 0), "close": (15, 0), "name": "Tokyo Stock Exchange"},
    "HKEX": {"tz": "Asia/Hong_Kong", "open": (9, 30), "close": (16, 0), "name": "Hong Kong Exchange"},
    "SSE": {"tz": "Asia/Shanghai", "open": (9, 30), "close": (15, 0), "name": "Shanghai Stock Exchange"},
    "EURONEXT": {"tz": "Europe/Paris", "open": (9, 0), "close": (17, 30), "name": "Euronext"},
    "ASX": {"tz": "Australia/Sydney", "open": (10, 0), "close": (16, 0), "name": "Australian Securities Exchange"},
    "BSE": {"tz": "Asia/Kolkata", "open": (9, 15), "close": (15, 30), "name": "Bombay Stock Exchange"},
    "CRYPTO": {"tz": "UTC", "open": (0, 0), "close": (23, 59), "name": "Crypto (24/7)"},
}

# ---------------------------------------------------------------------------
# Major holidays by country (2026, updatable annually)
# Format: {country_code: [(month, day, name), ...]}
# ---------------------------------------------------------------------------
HOLIDAYS_2026 = {
    "US": [
        (1, 1, "New Year's Day"), (1, 19, "MLK Day"), (2, 16, "Presidents' Day"),
        (5, 25, "Memorial Day"), (7, 4, "Independence Day"), (9, 7, "Labor Day"),
        (11, 26, "Thanksgiving"), (12, 25, "Christmas Day"),
    ],
    "UK": [
        (1, 1, "New Year's Day"), (4, 3, "Good Friday"), (4, 6, "Easter Monday"),
        (5, 4, "Early May Bank Holiday"), (5, 25, "Spring Bank Holiday"),
        (8, 31, "Summer Bank Holiday"), (12, 25, "Christmas Day"), (12, 28, "Boxing Day (substitute)"),
    ],
    "PT": [
        (1, 1, "New Year's Day"), (4, 3, "Good Friday"), (4, 5, "Easter Sunday"),
        (4, 25, "Freedom Day"), (5, 1, "Labour Day"), (6, 4, "Corpus Christi"),
        (6, 10, "Portugal Day"), (8, 15, "Assumption"), (10, 5, "Republic Day"),
        (11, 1, "All Saints' Day"), (12, 1, "Restoration of Independence"), (12, 8, "Immaculate Conception"),
        (12, 25, "Christmas Day"),
    ],
    "JP": [
        (1, 1, "New Year's Day"), (1, 12, "Coming of Age Day"), (2, 11, "National Foundation Day"),
        (2, 23, "Emperor's Birthday"), (3, 20, "Vernal Equinox Day"), (4, 29, "Showa Day"),
        (5, 3, "Constitution Memorial Day"), (5, 4, "Greenery Day"), (5, 5, "Children's Day"),
        (7, 20, "Marine Day"), (8, 11, "Mountain Day"), (9, 21, "Respect for the Aged Day"),
        (9, 23, "Autumnal Equinox"), (10, 12, "Sports Day"), (11, 3, "Culture Day"),
        (11, 23, "Labour Thanksgiving"), (12, 23, "Emperor's Birthday"),
    ],
}

# Timezone aliases — map common names to IANA identifiers
TZ_ALIASES = {
    "EST": "America/New_York", "EDT": "America/New_York",
    "CST": "America/Chicago", "CDT": "America/Chicago",
    "MST": "America/Denver", "MDT": "America/Denver",
    "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
    "GMT": "Europe/London", "BST": "Europe/London",
    "CET": "Europe/Paris", "CEST": "Europe/Paris",
    "WET": "Europe/Lisbon", "WEDT": "Europe/Lisbon", "WEST": "Europe/Lisbon",
    "JST": "Asia/Tokyo",
    "HKT": "Asia/Hong_Kong",
    "IST": "Asia/Kolkata",
    "AEST": "Australia/Sydney", "AEDT": "Australia/Sydney",
    "UTC": "UTC",
}


def _resolve_tz(tz_str: str) -> ZoneInfo:
    """Resolve timezone string to ZoneInfo, handling aliases."""
    alias = TZ_ALIASES.get(tz_str.upper())
    if alias:
        return ZoneInfo(alias)
    try:
        return ZoneInfo(tz_str)
    except Exception:
        return ZoneInfo("UTC")


def _market_status(exchange: dict, now_utc: datetime) -> dict:
    """Get market open/close status for an exchange."""
    tz = ZoneInfo(exchange["tz"])
    local = now_utc.astimezone(tz)

    open_h, open_m = exchange["open"]
    close_h, close_m = exchange["close"]

    market_open = local.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
    market_close = local.replace(hour=close_h, minute=close_m, second=0, microsecond=0)

    is_weekend = local.weekday() >= 5
    # Crypto never closes
    if exchange["tz"] == "UTC" and exchange["open"] == (0, 0):
        return {"status": "open", "note": "24/7"}

    if is_weekend:
        return {"status": "closed", "reason": "weekend"}

    if local < market_open:
        mins = int((market_open - local).total_seconds() / 60)
        return {"status": "closed", "opens_in": f"{mins // 60}h{mins % 60}m"}
    elif local > market_close:
        return {"status": "closed", "reason": "after hours"}
    else:
        mins = int((market_close - local).total_seconds() / 60)
        return {"status": "open", "closes_in": f"{mins // 60}h{mins % 60}m"}


def _next_holiday(country: str, now: datetime) -> dict | None:
    """Get next upcoming holiday for a country."""
    holidays = HOLIDAYS_2026.get(country)
    if not holidays:
        return None

    year = now.year
    for month, day, name in holidays:
        try:
            hdate = datetime(year, month, day)
            if hdate.date() >= now.date():
                days_until = (hdate.date() - now.date()).days
                return {"date": hdate.strftime("%Y-%m-%d"), "name": name, "days_until": days_until}
        except ValueError:
            continue
    return None


def get_world_context(timezone_str: str = "UTC", country: str = "", exchanges: list[str] | None = None) -> dict:
    """
    Get full world context for an AI agent session.

    Args:
        timezone_str: IANA timezone or alias (e.g., "Europe/Lisbon", "WEDT", "EST")
        country: ISO country code for holidays (e.g., "US", "PT", "UK")
        exchanges: List of exchange codes (e.g., ["NYSE", "LSE"]). None = all major.
    """
    tz = _resolve_tz(timezone_str)
    now_utc = datetime.now(ZoneInfo("UTC"))
    now_local = now_utc.astimezone(tz)

    # UTC offset
    offset = now_local.utcoffset()
    offset_hours = offset.total_seconds() / 3600 if offset else 0
    offset_str = f"UTC{'+' if offset_hours >= 0 else ''}{offset_hours:g}"

    # DST detection
    dst = now_local.dst()
    dst_active = dst is not None and dst.total_seconds() > 0

    # Day info
    is_weekend = now_local.weekday() >= 5
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Markets
    if exchanges is None:
        exchanges = ["NYSE", "NASDAQ", "LSE", "EURONEXT", "TSE", "CRYPTO"]
    markets = {}
    for code in exchanges:
        if code in EXCHANGES:
            ex = EXCHANGES[code]
            markets[code] = {
                "name": ex["name"],
                **_market_status(ex, now_utc),
            }

    # Holidays
    holiday = _next_holiday(country.upper(), now_local) if country else None
    # Try common countries if none specified
    if not holiday and not country:
        for c in ["US", "PT", "UK"]:
            h = _next_holiday(c, now_local)
            if h:
                holiday = {**h, "country": c}
                break

    # Quarter
    quarter = f"Q{(now_local.month - 1) // 3 + 1}"
    week_number = now_local.isocalendar()[1]

    return {
        "utc": now_utc.isoformat(),
        "local_time": now_local.isoformat(),
        "timezone": str(tz),
        "timezone_abbrev": now_local.strftime("%Z"),
        "utc_offset": offset_str,
        "dst_active": dst_active,
        "day_of_week": day_names[now_local.weekday()],
        "is_weekend": is_weekend,
        "is_business_hours": not is_weekend and 9 <= now_local.hour < 18,
        "quarter": quarter,
        "week_number": week_number,
        "day_of_year": now_local.timetuple().tm_yday,
        "markets": markets,
        "next_holiday": holiday,
    }


if __name__ == "__main__":
    import pprint
    pprint.pprint(get_world_context("Europe/Lisbon", "PT"))
