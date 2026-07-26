"""Pay-period and custom date-range helpers.

The default pay period runs from the 26th of the previous month through the
25th of the current/next month. Public CLI input uses explicit ISO date ranges.
"""

from __future__ import annotations

import datetime as _dt

import config

PERIOD_START_DAY = 26
PERIOD_END_DAY = 25
DATE_FORMAT_HINT = "YYYY-MM-DD"


def compute_period(reference: _dt.date | None = None) -> tuple[_dt.date, _dt.date]:
    """Return (start_date, end_date) for the period containing `reference`.

    Rule: 26th of previous month -> 25th of current month.

    If the reference day is the 26th or later, the period is
    [26th this month .. 25th next month]; otherwise it is
    [26th previous month .. 25th this month].
    """
    today = reference or _dt.date.today()

    if today.day >= PERIOD_START_DAY:
        start = today.replace(day=PERIOD_START_DAY)
        end = _add_month(start).replace(day=PERIOD_END_DAY)
    else:
        end = today.replace(day=PERIOD_END_DAY)
        start = _sub_month(today).replace(day=PERIOD_START_DAY)
    return start, end


def parse_date(value: str, label: str = "Date") -> _dt.date:
    """Parse one ISO date, raising ValueError with a user-facing message."""
    raw = value.strip()
    if not raw:
        raise ValueError(f"{label} cannot be blank.")
    try:
        return _dt.date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{label} must use {DATE_FORMAT_HINT}.") from exc


def validate_range(start: _dt.date, end: _dt.date) -> tuple[_dt.date, _dt.date]:
    """Validate and return an inclusive date range."""
    if start > end:
        raise ValueError("Start date must be on or before end date.")
    return start, end


def parse_range(start_value: str, end_value: str) -> tuple[_dt.date, _dt.date]:
    """Parse and validate an inclusive ISO date range."""
    start = parse_date(start_value, "Start date")
    end = parse_date(end_value, "End date")
    return validate_range(start, end)


def parse_range_args(argv: list[str]) -> tuple[_dt.date, _dt.date]:
    """Parse CLI date-range args.

    Accepts no args for the current default period, or exactly:
    --start YYYY-MM-DD --end YYYY-MM-DD
    """
    if not argv:
        return compute_period()
    if len(argv) != 4:
        raise ValueError("Use no arguments, or provide both --start and --end.")

    values: dict[str, str] = {}
    i = 0
    while i < len(argv):
        flag = argv[i]
        if flag not in {"--start", "--end"}:
            raise ValueError(f"Unknown argument: {flag}")
        if flag in values:
            raise ValueError(f"{flag} was provided more than once.")
        values[flag] = argv[i + 1]
        i += 2

    return parse_range(values["--start"], values["--end"])


def target_dates(start: _dt.date, end: _dt.date) -> list[_dt.date]:
    """All dates in [start, end] whose weekday is in config.WORK_WEEKDAYS."""
    days: list[_dt.date] = []
    cur = start
    one = _dt.timedelta(days=1)
    while cur <= end:
        if cur.weekday() in config.WORK_WEEKDAYS:
            days.append(cur)
        cur += one
    return days


def _add_month(d: _dt.date) -> _dt.date:
    year = d.year + (1 if d.month == 12 else 0)
    month = 1 if d.month == 12 else d.month + 1
    return d.replace(year=year, month=month, day=1)


def _sub_month(d: _dt.date) -> _dt.date:
    year = d.year - (1 if d.month == 1 else 0)
    month = 12 if d.month == 1 else d.month - 1
    return d.replace(year=year, month=month, day=1)


if __name__ == "__main__":  # pragma: no cover
    import sys

    try:
        s, e = parse_range_args(sys.argv[1:])
    except ValueError as exc:
        print(f"Error: {exc}")
        print("Usage: python period.py [--start YYYY-MM-DD --end YYYY-MM-DD]")
        sys.exit(2)
    days = target_dates(s, e)
    print(f"Date range: {s.isoformat()} .. {e.isoformat()}")
    print(f"Work days to fill ({len(days)}):")
    for d in days:
        print(f"  {d.isoformat()}  ({d.strftime('%a')})")
