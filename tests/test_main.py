import datetime as dt
import unittest
from unittest.mock import MagicMock, Mock, call, patch

import main


class MainOptionTests(unittest.TestCase):
    def test_parse_run_options_defaults_to_current_period(self) -> None:
        options = main.parse_run_options([])
        self.assertLessEqual(options.start, options.end)
        self.assertFalse(options.auto_submit)

    def test_parse_run_options_supports_auto_submit_and_range(self) -> None:
        options = main.parse_run_options(
            ["--auto-submit", "--start", "2026-05-01", "--end", "2026-05-31"]
        )
        self.assertEqual(options.start, dt.date(2026, 5, 1))
        self.assertEqual(options.end, dt.date(2026, 5, 31))
        self.assertTrue(options.auto_submit)

    def test_parse_run_options_rejects_duplicate_auto_submit(self) -> None:
        with self.assertRaisesRegex(ValueError, "both --start and --end"):
            main.parse_run_options(["--auto-submit", "--auto-submit"])

    def test_choose_period_cli_returns_only_dates(self) -> None:
        self.assertEqual(
            main.choose_period(
                ["main.py", "--start", "2026-05-01", "--end", "2026-05-31"]
            ),
            (dt.date(2026, 5, 1), dt.date(2026, 5, 31)),
        )

    def test_choose_period_cli_error_exits(self) -> None:
        with self.assertRaises(SystemExit) as cm, patch("builtins.print") as printed:
            main.choose_period(["main.py", "6"])
        self.assertEqual(cm.exception.code, 2)
        printed.assert_has_calls(
            [
                call("Error: Use no arguments, or provide both --start and --end."),
                call("Usage: python main.py [--auto-submit] [--start YYYY-MM-DD --end YYYY-MM-DD]"),
            ]
        )

    def test_choose_period_interactive_blank_uses_default(self) -> None:
        default = (dt.date(2026, 6, 26), dt.date(2026, 7, 25))
        with patch.object(main.period, "compute_period", return_value=default), patch(
            "builtins.input", return_value=""
        ), patch("builtins.print"):
            self.assertEqual(main.choose_period(["main.py"]), default)

    def test_choose_period_interactive_retries_invalid_then_accepts(self) -> None:
        with patch.object(
            main.period,
            "compute_period",
            return_value=(dt.date(2026, 6, 26), dt.date(2026, 7, 25)),
        ), patch("builtins.input", side_effect=["bad", "2026-05-31", "2026-05-01", "2026-05-31"]), patch(
            "builtins.print"
        ) as printed:
            self.assertEqual(
                main.choose_period(["main.py"]),
                (dt.date(2026, 5, 1), dt.date(2026, 5, 31)),
            )
        printed.assert_any_call("  Start date must use YYYY-MM-DD.")

    def test_choose_run_options_cli_auto_submit(self) -> None:
        options = main.choose_run_options(["main.py", "--auto-submit"])
        self.assertTrue(options.auto_submit)
        self.assertLessEqual(options.start, options.end)

    def test_choose_run_options_cli_error_exits(self) -> None:
        with self.assertRaises(SystemExit) as cm, patch("builtins.print"):
            main.choose_run_options(["main.py", "--bogus"])
        self.assertEqual(cm.exception.code, 2)

    def test_choose_run_options_interactive_defaults_to_manual(self) -> None:
        with patch.object(
            main, "choose_period", return_value=(dt.date(2026, 5, 1), dt.date(2026, 5, 31))
        ):
            options = main.choose_run_options(["main.py"])
        self.assertEqual(options.start, dt.date(2026, 5, 1))
        self.assertEqual(options.end, dt.date(2026, 5, 31))
        self.assertFalse(options.auto_submit)


class MainHoursTests(unittest.TestCase):
    def test_fmt_formats_minutes_as_hhmm(self) -> None:
        self.assertEqual(main._fmt(8 * 60 + 5), "08:05")

    def test_generate_hours_applies_floor(self) -> None:
        with patch.object(main.random, "randint", side_effect=[8 * 60, 60]):
            self.assertEqual(main.generate_hours(30, 90, floor=120), ("08:00", "10:00", 120))

    def test_regular_and_half_hours_use_configured_ranges(self) -> None:
        with patch.object(main, "generate_hours", return_value=("08:00", "17:00", 540)) as gen:
            self.assertEqual(main.regular_hours(), ("08:00", "17:00", 540))
        gen.assert_called_once_with(
            main.config.DURATION_MIN_MINUTES,
            main.config.DURATION_MAX_MINUTES,
            main.config.MIN_DURATION_MINUTES,
        )

        with patch.object(main, "generate_hours", return_value=("08:00", "13:00", 300)) as gen:
            self.assertEqual(main.half_hours(), ("08:00", "13:00", 300))
        gen.assert_called_once_with(
            main.config.HALF_DURATION_MIN_MINUTES,
            main.config.HALF_DURATION_MAX_MINUTES,
        )


class MainHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = Mock()
        self.day = dt.date(2026, 5, 3)
        self.label = "[1/1] 2026-05-03 (Sun)"
        self.print_patcher = patch("builtins.print")
        self.print_patcher.start()

    def tearDown(self) -> None:
        self.print_patcher.stop()

    def test_fill_work_modal_prints_hours_and_fills_day(self) -> None:
        with patch.object(main, "fill_day", return_value=True) as fill_day, patch("builtins.print"):
            self.assertTrue(
                main._fill_work_modal(self.page, self.day, ("08:00", "17:00", 540), "hours")
            )
        fill_day.assert_called_once_with(self.page, self.day, "08:00", "17:00")

    def test_handle_work_auto_submit_saves_without_prompt(self) -> None:
        with patch.object(main, "regular_hours", return_value=("08:00", "17:00", 540)), patch.object(
            main, "_fill_work_modal", return_value=True
        ), patch.object(main, "submit_day") as submit, patch("builtins.input") as input_mock:
            self.assertEqual(main._handle_work(self.page, self.day, self.label, True), "continue")
        submit.assert_called_once_with(self.page, self.day)
        input_mock.assert_not_called()

    def test_handle_work_auto_submit_skips_fill_failure(self) -> None:
        with patch.object(main, "_fill_work_modal", return_value=False), patch.object(
            main, "_close_modal"
        ) as close_modal:
            self.assertEqual(main._handle_work(self.page, self.day, self.label, True), "continue")
        close_modal.assert_called_once_with(self.page)

    def test_handle_work_manual_submit_skip_and_quit_paths(self) -> None:
        with patch.object(main, "_fill_work_modal", return_value=True), patch.object(
            main, "submit_day"
        ) as submit, patch("builtins.input", return_value=""):
            self.assertEqual(main._handle_work(self.page, self.day, self.label), "continue")
        submit.assert_called_once_with(self.page, self.day)

        with patch.object(main, "_fill_work_modal", return_value=True), patch.object(
            main, "_close_modal"
        ) as close_modal, patch("builtins.input", return_value="s"):
            self.assertEqual(main._handle_work(self.page, self.day, self.label), "continue")
        close_modal.assert_called_once_with(self.page)

        with patch.object(main, "_fill_work_modal", return_value=True), patch.object(
            main, "_close_modal"
        ) as close_modal, patch("builtins.input", return_value="q"):
            self.assertEqual(main._handle_work(self.page, self.day, self.label), "quit")
        close_modal.assert_called_once_with(self.page)

    def test_handle_work_manual_fill_failure_paths(self) -> None:
        with patch.object(main, "_fill_work_modal", return_value=False), patch(
            "builtins.input", return_value="q"
        ):
            self.assertEqual(main._handle_work(self.page, self.day, self.label), "quit")

        with patch.object(main, "_fill_work_modal", return_value=False), patch(
            "builtins.input", return_value=""
        ):
            self.assertEqual(main._handle_work(self.page, self.day, self.label), "continue")

    def test_handle_erev_auto_submit_saves_half_day(self) -> None:
        with patch.object(main, "half_hours", return_value=("08:00", "13:00", 300)), patch.object(
            main, "_fill_work_modal", return_value=True
        ), patch.object(main, "submit_day") as submit, patch("builtins.input") as input_mock:
            self.assertEqual(
                main._handle_erev(self.page, self.day, self.label, "פסח", True),
                "continue",
            )
        submit.assert_called_once_with(self.page, self.day)
        input_mock.assert_not_called()

    def test_handle_erev_auto_submit_skips_fill_failure(self) -> None:
        with patch.object(main, "_fill_work_modal", return_value=False), patch.object(
            main, "_close_modal"
        ) as close_modal:
            self.assertEqual(
                main._handle_erev(self.page, self.day, self.label, "פסח", True),
                "continue",
            )
        close_modal.assert_called_once_with(self.page)

    def test_handle_erev_manual_submit_skip_quit_and_full_day_paths(self) -> None:
        with patch.object(main, "_fill_work_modal", return_value=True), patch.object(
            main, "submit_day"
        ) as submit, patch("builtins.input", return_value=""):
            self.assertEqual(main._handle_erev(self.page, self.day, self.label, "פסח"), "continue")
        submit.assert_called_once_with(self.page, self.day)

        with patch.object(main, "_fill_work_modal", return_value=True), patch.object(
            main, "_close_modal"
        ) as close_modal, patch("builtins.input", return_value="s"):
            self.assertEqual(main._handle_erev(self.page, self.day, self.label, "פסח"), "continue")
        close_modal.assert_called_once_with(self.page)

        with patch.object(main, "_fill_work_modal", return_value=True), patch.object(
            main, "_close_modal"
        ) as close_modal, patch("builtins.input", return_value="q"):
            self.assertEqual(main._handle_erev(self.page, self.day, self.label, "פסח"), "quit")
        close_modal.assert_called_once_with(self.page)

        with patch.object(main, "_fill_work_modal", side_effect=[True, True]) as fill, patch.object(
            main, "_close_modal"
        ), patch.object(main, "regular_hours", return_value=("08:00", "17:00", 540)), patch.object(
            main, "submit_day"
        ) as submit, patch(
            "builtins.input", side_effect=["f", ""]
        ):
            self.assertEqual(main._handle_erev(self.page, self.day, self.label, "פסח"), "continue")
        self.assertEqual(fill.call_count, 2)
        submit.assert_called_once_with(self.page, self.day)

        with patch.object(main, "_fill_work_modal", side_effect=[True, True]), patch.object(
            main, "_close_modal"
        ) as close_modal, patch.object(main, "regular_hours", return_value=("08:00", "17:00", 540)), patch(
            "builtins.input", side_effect=["f", "s"]
        ):
            self.assertEqual(main._handle_erev(self.page, self.day, self.label, "פסח"), "continue")
        self.assertGreaterEqual(close_modal.call_count, 2)

        with patch.object(main, "_fill_work_modal", side_effect=[True, False]), patch.object(
            main, "_close_modal"
        ) as close_modal, patch.object(main, "regular_hours", return_value=("08:00", "17:00", 540)), patch(
            "builtins.input", return_value="f"
        ):
            self.assertEqual(main._handle_erev(self.page, self.day, self.label, "פסח"), "continue")
        self.assertGreaterEqual(close_modal.call_count, 2)

    def test_handle_erev_manual_fill_failure_paths(self) -> None:
        with patch.object(main, "_fill_work_modal", return_value=False), patch(
            "builtins.input", return_value="q"
        ):
            self.assertEqual(main._handle_erev(self.page, self.day, self.label, "פסח"), "quit")

        with patch.object(main, "_fill_work_modal", return_value=False), patch(
            "builtins.input", return_value=""
        ):
            self.assertEqual(main._handle_erev(self.page, self.day, self.label, "פסח"), "continue")

    def test_handle_holiday_auto_submit_reports_holiday(self) -> None:
        with patch.object(main, "fill_holiday", return_value=True) as fill_holiday, patch.object(
            main, "submit_holiday"
        ) as submit, patch("builtins.input") as input_mock:
            self.assertEqual(
                main._handle_holiday(self.page, self.day, self.label, "יום כיפור", True),
                "continue",
            )
        fill_holiday.assert_called_once_with(self.page, self.day)
        submit.assert_called_once_with(self.page, self.day)
        input_mock.assert_not_called()

    def test_handle_holiday_auto_submit_skips_fill_failure(self) -> None:
        with patch.object(main, "fill_holiday", return_value=False), patch.object(
            main, "_close_modal"
        ) as close_modal:
            self.assertEqual(
                main._handle_holiday(self.page, self.day, self.label, "יום כיפור", True),
                "continue",
            )
        close_modal.assert_called_once_with(self.page)

    def test_handle_holiday_manual_quit_skip_work_and_holiday_paths(self) -> None:
        with patch("builtins.input", return_value="q"):
            self.assertEqual(main._handle_holiday(self.page, self.day, self.label, "יום כיפור"), "quit")

        with patch("builtins.input", return_value="s"):
            self.assertEqual(
                main._handle_holiday(self.page, self.day, self.label, "יום כיפור"),
                "continue",
            )

        with patch("builtins.input", side_effect=["w", ""]), patch.object(
            main, "_fill_work_modal", return_value=True
        ), patch.object(main, "regular_hours", return_value=("08:00", "17:00", 540)), patch.object(
            main, "submit_day"
        ) as submit:
            self.assertEqual(
                main._handle_holiday(self.page, self.day, self.label, "יום כיפור"),
                "continue",
            )
        submit.assert_called_once_with(self.page, self.day)

        with patch("builtins.input", side_effect=["w", "s"]), patch.object(
            main, "_fill_work_modal", return_value=True
        ), patch.object(main, "regular_hours", return_value=("08:00", "17:00", 540)), patch.object(
            main, "_close_modal"
        ) as close_modal:
            self.assertEqual(
                main._handle_holiday(self.page, self.day, self.label, "יום כיפור"),
                "continue",
            )
        close_modal.assert_called_once_with(self.page)

        with patch("builtins.input", return_value="w"), patch.object(
            main, "_fill_work_modal", return_value=False
        ), patch.object(main, "regular_hours", return_value=("08:00", "17:00", 540)), patch.object(
            main, "_close_modal"
        ) as close_modal:
            self.assertEqual(
                main._handle_holiday(self.page, self.day, self.label, "יום כיפור"),
                "continue",
            )
        close_modal.assert_called_once_with(self.page)

        with patch("builtins.input", side_effect=["", ""]), patch.object(
            main, "fill_holiday", return_value=True
        ), patch.object(main, "submit_holiday") as submit:
            self.assertEqual(
                main._handle_holiday(self.page, self.day, self.label, "יום כיפור"),
                "continue",
            )
        submit.assert_called_once_with(self.page, self.day)

        with patch("builtins.input", side_effect=["", "s"]), patch.object(
            main, "fill_holiday", return_value=True
        ), patch.object(main, "_close_modal") as close_modal:
            self.assertEqual(
                main._handle_holiday(self.page, self.day, self.label, "יום כיפור"),
                "continue",
            )
        close_modal.assert_called_once_with(self.page)

        with patch("builtins.input", return_value=""), patch.object(
            main, "fill_holiday", return_value=False
        ), patch.object(main, "_close_modal") as close_modal:
            self.assertEqual(
                main._handle_holiday(self.page, self.day, self.label, "יום כיפור"),
                "continue",
            )
        close_modal.assert_called_once_with(self.page)


class MainLoopTests(unittest.TestCase):
    def _playwright_mock(self, pages: list[Mock] | None = None) -> tuple[MagicMock, Mock, Mock, Mock]:
        page = Mock(name="page")
        context = Mock(name="context")
        context.pages = [page] if pages is None else pages
        if pages == []:
            context.new_page.return_value = page

        playwright = Mock(name="playwright")
        playwright.chromium.launch_persistent_context.return_value = context

        manager = MagicMock(name="sync_playwright_manager")
        manager.__enter__.return_value = playwright
        manager.__exit__.return_value = None
        return manager, playwright, context, page

    def test_main_returns_before_browser_when_no_target_days(self) -> None:
        options = main.RunOptions(
            start=dt.date(2026, 5, 1),
            end=dt.date(2026, 5, 2),
            auto_submit=True,
        )
        with patch.object(main, "choose_run_options", return_value=options), patch.object(
            main.period, "target_dates", return_value=[]
        ), patch.object(main.random, "seed"), patch.object(main, "sync_playwright") as sync, patch(
            "builtins.print"
        ):
            main.main()
        sync.assert_not_called()

    def test_main_routes_work_erev_and_holiday_days_end_to_end(self) -> None:
        start = dt.date(2026, 5, 3)
        end = dt.date(2026, 5, 5)
        days = [start, dt.date(2026, 5, 4), end]
        options = main.RunOptions(start=start, end=end, auto_submit=True)
        manager, playwright, context, page = self._playwright_mock()

        with patch.object(main, "choose_run_options", return_value=options), patch.object(
            main.period, "target_dates", return_value=days
        ) as target_dates, patch.object(
            main.holiday_calendar, "years_for", return_value={2026}
        ) as years_for, patch.object(
            main.holiday_calendar, "full_holidays", return_value={days[2]: "יום כיפור"}
        ) as full_holidays, patch.object(
            main.holiday_calendar, "erev_days", return_value={days[1]: "פסח"}
        ) as erev_days, patch.object(
            main.holiday_calendar,
            "classify",
            side_effect=[("work", None), ("erev", "פסח"), ("holiday", "יום כיפור")],
        ) as classify, patch.object(
            main, "ensure_logged_in"
        ) as ensure_logged_in, patch.object(
            main, "_handle_work", return_value="continue"
        ) as handle_work, patch.object(
            main, "_handle_erev", return_value="continue"
        ) as handle_erev, patch.object(
            main, "_handle_holiday", return_value="continue"
        ) as handle_holiday, patch.object(
            main, "sync_playwright", return_value=manager
        ), patch.object(
            main.random, "seed"
        ), patch(
            "builtins.print"
        ):
            main.main()

        target_dates.assert_called_once_with(start, end)
        years_for.assert_called_once_with(start, end)
        full_holidays.assert_called_once_with({2026})
        erev_days.assert_called_once_with({2026})
        classify.assert_has_calls(
            [
                call(days[0], {days[2]: "יום כיפור"}, {days[1]: "פסח"}),
                call(days[1], {days[2]: "יום כיפור"}, {days[1]: "פסח"}),
                call(days[2], {days[2]: "יום כיפור"}, {days[1]: "פסח"}),
            ]
        )
        playwright.chromium.launch_persistent_context.assert_called_once_with(
            user_data_dir=main.config.USER_DATA_DIR,
            headless=main.config.HEADLESS,
            slow_mo=main.config.SLOW_MO_MS,
        )
        context.set_default_timeout.assert_called_once_with(main.config.DEFAULT_TIMEOUT_MS)
        ensure_logged_in.assert_called_once_with(page)
        page.goto.assert_called_once_with(
            main.config.PRESENCE_URL.format(start=start.isoformat(), end=end.isoformat()),
            wait_until="domcontentloaded",
        )
        page.wait_for_load_state.assert_called_once_with("networkidle", timeout=15000)
        handle_work.assert_called_once_with(
            page, days[0], "[1/3] 2026-05-03 (Sun)", True
        )
        handle_erev.assert_called_once_with(
            page, days[1], "[2/3] 2026-05-04 (Mon)", "פסח", True
        )
        handle_holiday.assert_called_once_with(
            page, days[2], "[3/3] 2026-05-05 (Tue)", "יום כיפור", True
        )
        context.close.assert_called_once_with()

    def test_main_stops_after_quit_and_closes_browser(self) -> None:
        start = dt.date(2026, 5, 3)
        days = [start, dt.date(2026, 5, 4)]
        options = main.RunOptions(start=start, end=days[1], auto_submit=False)
        manager, _, context, page = self._playwright_mock()

        with patch.object(main, "choose_run_options", return_value=options), patch.object(
            main.period, "target_dates", return_value=days
        ), patch.object(main.holiday_calendar, "years_for", return_value={2026}), patch.object(
            main.holiday_calendar, "full_holidays", return_value={}
        ), patch.object(
            main.holiday_calendar, "erev_days", return_value={}
        ), patch.object(
            main.holiday_calendar, "classify", return_value=("work", None)
        ) as classify, patch.object(
            main, "ensure_logged_in"
        ), patch.object(
            main, "_handle_work", return_value="quit"
        ) as handle_work, patch.object(
            main, "sync_playwright", return_value=manager
        ), patch.object(
            main.random, "seed"
        ), patch(
            "builtins.input"
        ) as input_mock, patch(
            "builtins.print"
        ):
            main.main()

        classify.assert_called_once_with(days[0], {}, {})
        handle_work.assert_called_once_with(page, days[0], "[1/2] 2026-05-03 (Sun)", False)
        input_mock.assert_called_once_with("Press Enter to close the browser window... ")
        context.close.assert_called_once_with()

    def test_main_uses_new_page_when_context_has_no_pages(self) -> None:
        day = dt.date(2026, 5, 3)
        options = main.RunOptions(start=day, end=day, auto_submit=True)
        manager, _, context, page = self._playwright_mock(pages=[])

        with patch.object(main, "choose_run_options", return_value=options), patch.object(
            main.period, "target_dates", return_value=[day]
        ), patch.object(main.holiday_calendar, "years_for", return_value={2026}), patch.object(
            main.holiday_calendar, "full_holidays", return_value={}
        ), patch.object(
            main.holiday_calendar, "erev_days", return_value={}
        ), patch.object(
            main.holiday_calendar, "classify", return_value=("work", None)
        ), patch.object(
            main, "ensure_logged_in"
        ) as ensure_logged_in, patch.object(
            main, "_handle_work", return_value="continue"
        ), patch.object(
            main, "sync_playwright", return_value=manager
        ), patch.object(
            main.random, "seed"
        ), patch(
            "builtins.print"
        ):
            main.main()

        context.new_page.assert_called_once_with()
        ensure_logged_in.assert_called_once_with(page)
        context.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
