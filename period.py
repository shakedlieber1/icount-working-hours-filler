"""Pay-period date helpers.

The pay period runs from the 26th of the previous month through the 25th of
the selected/current month.
"""

from __future__ import annotations

import datetime as _dt

import config

PERIOD_START_DAY = 26
PERIOD_END_DAY = 25


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


def compute_period_for_month(month: int, year: int | None = None) -> tuple[_dt.date, _dt.date]:
    """Return the period ending on the 25th of `month`/`year`.

    Example: month=6, year=2026 -> 2026-05-26 .. 2026-06-25.
    If `year` is omitted, the current year is used.
    """
    _validate_month(month)
    selected_year = year if year is not None else _dt.date.today().year
    end = _dt.date(selected_year, month, PERIOD_END_DAY)
    start = _sub_month(end).replace(day=PERIOD_START_DAY)
    return start, end


def parse_month_selection(value: str, default_year: int | None = None) -> tuple[int, int]:
    """Parse `M`, `MM`, or `YYYY-MM` into (month, year)."""
    raw = value.strip()
    if not raw:
        raise ValueError("Month cannot be blank.")

    year = default_year if default_year is not None else _dt.date.today().year
    if "-" in raw:
        parts = raw.split("-")
        if len(parts) != 2 or len(parts[0]) != 4 or not all(p.isdigit() for p in parts):
            raise ValueError("Use a month number like 6, or a year-month like 2026-06.")
        year = int(parts[0])
        month = int(parts[1])
    elif raw.isdigit():
        month = int(raw)
    else:
        raise ValueError("Use a month number like 6, or a year-month like 2026-06.")

    _validate_month(month)
    if year < 1:
        raise ValueError("Year must be positive.")
    return month, year


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


def _validate_month(month: int) -> None:
    if not 1 <= month <= 12:
        raise ValueError("Month must be a number from 1 to 12.")


def _add_month(d: _dt.date) -> _dt.date:
    year = d.year + (1 if d.month == 12 else 0)
    month = 1 if d.month == 12 else d.month + 1
    return d.replace(year=year, month=month, day=1)


def _sub_month(d: _dt.date) -> _dt.date:
    year = d.year - (1 if d.month == 1 else 0)
    month = 12 if d.month == 1 else d.month - 1
    return d.replace(year=year, month=month, day=1)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 2:
        print("Usage: python period.py [month|YYYY-MM]")
        sys.exit(2)

    if len(sys.argv) == 2:
        try:
            selected_month, selected_year = parse_month_selection(sys.argv[1])
            s, e = compute_period_for_month(selected_month, selected_year)
        except ValueError as exc:
            print(f"Error: {exc}")
            print("Usage: python period.py [month|YYYY-MM]")
            sys.exit(2)
    else:
        s, e = compute_period()
    days = target_dates(s, e)
    print(f"Period: {s.isoformat()} .. {e.isoformat()}")
    print(f"Work days to fill ({len(days)}):")
    for d in days:
        print(f"  {d.isoformat()}  ({d.strftime('%a')})")
