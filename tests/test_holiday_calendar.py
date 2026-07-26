import datetime as dt
import unittest
from unittest.mock import patch

import holiday_calendar


class HolidayCalendarTests(unittest.TestCase):
    def test_israel_returns_hebrew_holiday_calendar(self) -> None:
        calendar = holiday_calendar._israel({2026})
        self.assertTrue(hasattr(calendar, "items"))

    def test_years_for_includes_previous_start_and_end_years(self) -> None:
        self.assertEqual(
            holiday_calendar.years_for(dt.date(2026, 12, 26), dt.date(2027, 1, 25)),
            {2025, 2026, 2027},
        )

    def test_full_holidays_returns_israel_holiday_mapping(self) -> None:
        fake = {dt.date(2026, 9, 21): "יום כיפור"}
        with patch.object(holiday_calendar, "_israel", return_value=fake) as israel:
            self.assertEqual(holiday_calendar.full_holidays({2026}), fake)
        israel.assert_called_once_with({2026})

    def test_erev_days_excludes_independence_day(self) -> None:
        fake = {dt.date(2026, 4, 22): "יום העצמאות"}
        with patch.object(holiday_calendar, "_israel", return_value=fake):
            self.assertEqual(holiday_calendar.erev_days({2026}), {})

    def test_erev_days_uses_day_before_first_non_independence_holiday(self) -> None:
        fake = {
            dt.date(2026, 9, 21): "יום כיפור",
            dt.date(2026, 9, 22): "סוכות",
            dt.date(2026, 10, 3): "סוכות",
            dt.date(2026, 10, 4): "שמחת תורה",
        }
        with patch.object(holiday_calendar, "_israel", return_value=fake):
            self.assertEqual(
                holiday_calendar.erev_days({2026}),
                {
                    dt.date(2026, 9, 20): "יום כיפור",
                    dt.date(2026, 10, 2): "סוכות",
                },
            )

    def test_classify_prefers_full_holiday_then_erev_then_work(self) -> None:
        full = {dt.date(2026, 9, 21): "יום כיפור"}
        erev = {
            dt.date(2026, 9, 20): "יום כיפור",
            dt.date(2026, 9, 21): "ignored",
        }
        self.assertEqual(
            holiday_calendar.classify(dt.date(2026, 9, 21), full, erev),
            ("holiday", "יום כיפור"),
        )
        self.assertEqual(
            holiday_calendar.classify(dt.date(2026, 9, 20), full, erev),
            ("erev", "יום כיפור"),
        )
        self.assertEqual(
            holiday_calendar.classify(dt.date(2026, 9, 22), full, erev),
            ("work", None),
        )


if __name__ == "__main__":
    unittest.main()
