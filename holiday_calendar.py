"""Offline Israeli holiday + erev-chag classification.

Uses the `holidays` library (no network). "Full holidays" are the PUBLIC
category for Israel (Jewish Yom Tov + civil Independence Day). "Erev" days are
the work day immediately before a Jewish Yom Tov (Independence Day has no erev).
"""

from __future__ import annotations

import datetime as _dt
from typing import Iterable

import holidays

import config

# Substring identifying Israeli Independence Day in the Hebrew holiday name.
# Independence Day is a full day off but has no (shortened) erev.
_INDEPENDENCE = "עצמאות"


def _israel(years: Iterable[int]):
    return holidays.Israel(
        years=sorted(set(years)),
        categories=config.HOLIDAY_CATEGORIES,
        language="he",
    )


def years_for(start: _dt.date, end: _dt.date) -> set[int]:
    # Include the year before start so an erev on Dec 31 -> Jan 1 holiday resolves.
    return {start.year - 1, start.year, end.year}


def full_holidays(years: Iterable[int]) -> dict[_dt.date, str]:
    """Map of full-holiday date -> Hebrew name."""
    return dict(_israel(years))


def erev_days(years: Iterable[int]) -> dict[_dt.date, str]:
    """Map of erev (shortened) date -> name of the chag it precedes.

    An erev is the day before a Jewish Yom Tov, provided that previous day is
    not itself a holiday (so multi-day chagim only get one erev, at the start).
    Independence Day is excluded.
    """
    pub = _israel(years)
    one = _dt.timedelta(days=1)
    erev: dict[_dt.date, str] = {}
    for day, name in pub.items():
        if _INDEPENDENCE in name:
            continue
        prev = day - one
        if prev not in pub:
            erev.setdefault(prev, name)
    return erev


def classify(
    day: _dt.date,
    full: dict[_dt.date, str],
    erev: dict[_dt.date, str],
) -> tuple[str, str | None]:
    """Return ('holiday'|'erev'|'work', name_or_None) for a date."""
    if day in full:
        return "holiday", full[day]
    if day in erev:
        return "erev", erev[day]
    return "work", None


if __name__ == "__main__":  # pragma: no cover
    import sys

    ref = _dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else _dt.date.today()
    import period

    start, end = period.compute_period(ref)
    years = years_for(start, end)
    full = full_holidays(years)
    erev = erev_days(years)
    print(f"Reference {ref} -> period {start} .. {end}")
    for d in period.target_dates(start, end):
        kind, name = classify(d, full, erev)
        if kind != "work":
            print(f"  {d} ({d:%a})  {kind.upper():8} {name}")
