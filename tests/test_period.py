import datetime as dt
import unittest

import period


class PeriodSelectionTests(unittest.TestCase):
    def test_default_period_before_26th(self) -> None:
        self.assertEqual(
            period.compute_period(dt.date(2026, 7, 25)),
            (dt.date(2026, 6, 26), dt.date(2026, 7, 25)),
        )

    def test_default_period_on_or_after_26th(self) -> None:
        self.assertEqual(
            period.compute_period(dt.date(2026, 7, 26)),
            (dt.date(2026, 7, 26), dt.date(2026, 8, 25)),
        )

    def test_default_period_crosses_year_before_26th(self) -> None:
        self.assertEqual(
            period.compute_period(dt.date(2026, 1, 10)),
            (dt.date(2025, 12, 26), dt.date(2026, 1, 25)),
        )

    def test_default_period_crosses_year_after_26th(self) -> None:
        self.assertEqual(
            period.compute_period(dt.date(2026, 12, 26)),
            (dt.date(2026, 12, 26), dt.date(2027, 1, 25)),
        )

    def test_parse_date_strips_whitespace(self) -> None:
        self.assertEqual(
            period.parse_date(" 2026-05-01 ", "Start date"),
            dt.date(2026, 5, 1),
        )

    def test_blank_date_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be blank"):
            period.parse_date(" ", "Start date")

    def test_valid_explicit_range(self) -> None:
        self.assertEqual(
            period.parse_range("2026-05-01", "2026-05-31"),
            (dt.date(2026, 5, 1), dt.date(2026, 5, 31)),
        )

    def test_single_day_range_is_valid(self) -> None:
        self.assertEqual(
            period.parse_range("2026-05-01", "2026-05-01"),
            (dt.date(2026, 5, 1), dt.date(2026, 5, 1)),
        )

    def test_invalid_date_format_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            period.parse_range("05/01/2026", "2026-05-31")

    def test_start_after_end_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "on or before"):
            period.parse_range("2026-06-01", "2026-05-31")

    def test_cli_range_accepts_start_end_order(self) -> None:
        self.assertEqual(
            period.parse_range_args(
                ["--start", "2026-05-01", "--end", "2026-05-31"]
            ),
            (dt.date(2026, 5, 1), dt.date(2026, 5, 31)),
        )

    def test_cli_range_accepts_end_start_order(self) -> None:
        self.assertEqual(
            period.parse_range_args(
                ["--end", "2026-05-31", "--start", "2026-05-01"]
            ),
            (dt.date(2026, 5, 1), dt.date(2026, 5, 31)),
        )

    def test_cli_no_args_returns_default_range(self) -> None:
        start, end = period.parse_range_args([])
        self.assertLessEqual(start, end)

    def test_cli_missing_end_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "both --start and --end"):
            period.parse_range_args(["--start", "2026-05-01"])

    def test_cli_unknown_argument_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown argument"):
            period.parse_range_args(
                ["--from", "2026-05-01", "--end", "2026-05-31"]
            )

    def test_cli_duplicate_argument_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "more than once"):
            period.parse_range_args(
                ["--start", "2026-05-01", "--start", "2026-05-31"]
            )

    def test_cli_invalid_end_date_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "End date must use"):
            period.parse_range_args(
                ["--start", "2026-05-01", "--end", "2026-02-31"]
            )

    def test_target_dates_filters_configured_workdays(self) -> None:
        self.assertEqual(
            period.target_dates(dt.date(2026, 5, 1), dt.date(2026, 5, 3)),
            [dt.date(2026, 5, 3)],
        )

    def test_old_month_number_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "both --start and --end"):
            period.parse_range_args(["6"])

    def test_old_year_month_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "both --start and --end"):
            period.parse_range_args(["2026-06"])


if __name__ == "__main__":
    unittest.main()
