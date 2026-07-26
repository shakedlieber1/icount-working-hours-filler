"""Phase 2: fill working hours in icount, one day at a time.

For each work day (Sun-Thu) in the selected date range it generates random hours
(start 08:00-10:00, duration 9-11h, never below 8h), fills the day's time-in /
time-out fields in the visible browser, highlights them, then waits for you to
approve that day unless automatic submit mode is enabled.

Run:  python main.py        # prompts for the date range, defaulting to current period
      python main.py --start 2026-05-01 --end 2026-05-31
      python main.py --auto-submit --start 2026-05-01 --end 2026-05-31
"""

from __future__ import annotations

import datetime as _dt
import os
import random
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
from playwright.sync_api import (
    sync_playwright,
    Locator,
    Page,
    TimeoutError as PWTimeout,
)

import config
import holiday_calendar
import period


# ---------------------------------------------------------------------------
# Hours generation
# ---------------------------------------------------------------------------
def generate_hours(min_dur: int, max_dur: int, floor: int = 0) -> tuple[str, str, int]:
    """Return (start_hhmm, end_hhmm, duration_minutes) for one day.

    `min_dur`/`max_dur`/`floor` are in minutes.
    """
    start_min = random.randint(config.START_MIN_MINUTES, config.START_MAX_MINUTES)
    duration = random.randint(min_dur, max_dur)
    duration = max(duration, floor)
    end_min = start_min + duration
    return _fmt(start_min), _fmt(end_min), duration


def regular_hours() -> tuple[str, str, int]:
    return generate_hours(
        config.DURATION_MIN_MINUTES, config.DURATION_MAX_MINUTES, config.MIN_DURATION_MINUTES
    )


def half_hours() -> tuple[str, str, int]:
    return generate_hours(
        config.HALF_DURATION_MIN_MINUTES, config.HALF_DURATION_MAX_MINUTES
    )


def _fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# ---------------------------------------------------------------------------
# Period selection
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RunOptions:
    start: _dt.date
    end: _dt.date
    auto_submit: bool = False


def _usage() -> str:
    return "Usage: python main.py [--auto-submit] [--start YYYY-MM-DD --end YYYY-MM-DD]"


def parse_run_options(argv: list[str]) -> RunOptions:
    """Parse non-interactive run options from argv without the program name."""
    args = list(argv)
    auto_submit = False
    if "--auto-submit" in args:
        auto_submit = True
        args.remove("--auto-submit")

    start, end = period.parse_range_args(args)
    return RunOptions(start=start, end=end, auto_submit=auto_submit)


def choose_period(argv: list[str]) -> tuple[_dt.date, _dt.date]:
    """Resolve the fill period from CLI args or an interactive prompt."""
    if len(argv) > 1:
        try:
            options = parse_run_options(argv[1:])
            return options.start, options.end
        except ValueError as exc:
            print(f"Error: {exc}")
            print(_usage())
            sys.exit(2)

    default_start, default_end = period.compute_period()
    while True:
        print(
            "Date range to fill "
            f"[Enter={default_start.isoformat()} .. {default_end.isoformat()}]"
        )
        start_raw = input(f"  Start date ({period.DATE_FORMAT_HINT}): ").strip()
        if not start_raw:
            return default_start, default_end
        end_raw = input(f"  End date ({period.DATE_FORMAT_HINT}): ").strip()
        try:
            return period.parse_range(start_raw, end_raw)
        except ValueError as exc:
            print(f"  {exc}")


def choose_run_options(argv: list[str]) -> RunOptions:
    """Resolve all run options from CLI args or an interactive date prompt."""
    if len(argv) > 1:
        try:
            return parse_run_options(argv[1:])
        except ValueError as exc:
            print(f"Error: {exc}")
            print(_usage())
            sys.exit(2)

    start, end = choose_period(argv)
    return RunOptions(start=start, end=end)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def _fill_if_present(page: Page, selector: str, value: str) -> bool:  # pragma: no cover
    if not value:
        return False
    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=4000)
        loc.fill(value)
        return True
    except Exception:  # noqa: BLE001
        return False


def ensure_logged_in(page: Page) -> None:  # pragma: no cover
    user = os.environ.get("ICOUNT_USER", "")
    passwd = os.environ.get("ICOUNT_PASS", "")
    company = os.environ.get("ICOUNT_COMPANY", "")

    page.goto(config.LOGIN_URL, wait_until="domcontentloaded")

    # Already logged in (persistent profile)?
    try:
        page.locator(config.SELECTORS["logged_in_marker"]).first.wait_for(
            state="visible", timeout=4000
        )
        print("Already logged in (reused session).")
        return
    except PWTimeout:
        pass

    print("Logging in...")
    # icount may show a passkey screen first; switch to password login if so.
    try:
        chooser = page.locator(config.SELECTORS["passkey_password_chooser"]).first
        if chooser.is_visible(timeout=3000):
            chooser.click()
    except Exception:  # noqa: BLE001
        pass

    _fill_if_present(page, config.SELECTORS["login_company"], company)
    filled_user = _fill_if_present(page, config.SELECTORS["login_user"], user)
    filled_pass = _fill_if_present(page, config.SELECTORS["login_pass"], passwd)

    if filled_user and filled_pass:
        try:
            page.locator(config.SELECTORS["login_submit"]).first.click(timeout=5000)
        except Exception as exc:  # noqa: BLE001
            print(f"Could not click submit automatically ({exc}).")

    print("If a captcha / OTP / extra step appears, complete it in the browser window now.")
    input("Press Enter once you are fully logged in... ")


# ---------------------------------------------------------------------------
# Per-day fill (uses the page's own #punch_modal add-work-day flow)
# ---------------------------------------------------------------------------
def _highlight(loc: Locator) -> None:  # pragma: no cover
    try:
        loc.evaluate("el => { el.style.outline = '3px solid orange'; el.scrollIntoView({block:'center'}); }")
    except Exception:  # noqa: BLE001
        pass


def fill_day(page: Page, day: _dt.date, start_hhmm: str, end_hhmm: str) -> bool:  # pragma: no cover
    """Open the add-work-day modal for `day` and fill the time fields.

    Returns True if the modal is filled and ready to save.
    """
    iso = day.isoformat()
    isr = day.strftime("%d/%m/%Y")

    # Open the modal pre-set to this date using the page's own function.
    try:
        page.evaluate(config.JS_OPEN_PUNCH_MODAL, iso)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Could not open the add-work-day modal: {exc}")
        return False

    modal = page.locator(config.SELECTORS["punch_modal"])
    try:
        modal.wait_for(state="visible", timeout=8000)
    except PWTimeout:
        print("  ! Add-work-day modal did not appear.")
        return False

    try:
        # Force both the visible date fields and the hidden ISO fields so the
        # save posts the correct day regardless of datepicker quirks.
        page.locator(config.SELECTORS["punch_start_date"]).fill(isr)
        page.locator(config.SELECTORS["punch_end_date"]).fill(isr)
        page.eval_on_selector(config.SELECTORS["punch_iso_start_date"], "(el,v)=>el.value=v", iso)
        page.eval_on_selector(config.SELECTORS["punch_iso_end_date"], "(el,v)=>el.value=v", iso)

        start_in = page.locator(config.SELECTORS["punch_start_time"])
        end_in = page.locator(config.SELECTORS["punch_end_time"])
        start_in.fill(start_hhmm)
        end_in.fill(end_hhmm)
        start_in.dispatch_event("change")
        end_in.dispatch_event("change")

        _highlight(start_in)
        _highlight(end_in)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Failed to fill modal time fields for {iso}: {exc}")
        return False


def _close_modal(page: Page) -> None:  # pragma: no cover
    try:
        page.evaluate(
            "() => { if (window.jQuery) { jQuery('#punch_modal').modal('hide'); "
            "jQuery('#special_day_modal_new').modal('hide'); } }"
        )
        # Wait for bootstrap's close animation + backdrop removal to finish so a
        # subsequent modal can open cleanly.
        try:
            page.locator(".modal-backdrop").wait_for(state="hidden", timeout=3000)
        except Exception:  # noqa: BLE001
            page.wait_for_timeout(400)
    except Exception:  # noqa: BLE001
        pass


def fill_holiday(page: Page, day: _dt.date) -> bool:  # pragma: no cover
    """Open the absence modal and set it to a full-day holiday (יום חג)."""
    iso = day.isoformat()
    isr = day.strftime("%d/%m/%Y")

    try:
        page.evaluate(config.JS_OPEN_SPECIAL_DAY)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Could not open the absence modal: {exc}")
        return False

    modal = page.locator(config.SELECTORS["special_day_modal"])
    try:
        modal.wait_for(state="visible", timeout=8000)
    except PWTimeout:
        print("  ! Absence modal did not appear.")
        return False

    try:
        # The visible in-date field works; its change handler auto-fills the
        # (hidden) out-date in single-day mode. Set the visible in-date, then
        # force all hidden ISO + out-date values directly via JS.
        page.locator(config.SELECTORS["special_day_in_date"]).fill(isr)
        page.locator(config.SELECTORS["special_day_in_date"]).dispatch_event("change")
        page.eval_on_selector(config.SELECTORS["special_day_out_date"], "(el,v)=>el.value=v", isr)
        page.eval_on_selector(config.SELECTORS["special_day_iso_in"], "(el,v)=>el.value=v", iso)
        page.eval_on_selector(config.SELECTORS["special_day_iso_out"], "(el,v)=>el.value=v", iso)

        # The day-type <select> is hidden behind a bootstrap-select widget, so
        # set its value via JS, fire the page's onchange, and refresh the UI.
        page.eval_on_selector(
            config.SELECTORS["special_day_type"],
            """(el, v) => {
                el.value = v;
                el.dispatchEvent(new Event('change', { bubbles: true }));
                if (window.jQuery && jQuery(el).selectpicker) jQuery(el).selectpicker('refresh');
            }""",
            config.HOLIDAY_DAY_TYPE_ID,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Failed to fill the absence modal for {iso}: {exc}")
        return False


def submit_holiday(page: Page, day: _dt.date) -> None:  # pragma: no cover
    try:
        page.locator(config.SELECTORS["special_day_save"]).first.click(timeout=8000)
        try:
            page.locator(config.SELECTORS["special_day_modal"]).wait_for(state="hidden", timeout=8000)
            print(f"  Reported {day.isoformat()} as holiday (יום חג).")
        except PWTimeout:
            print(f"  ? Holiday sent for {day.isoformat()} but modal stayed open; check the browser.")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Could not save holiday for {day.isoformat()}: {exc}")
        print("    Click שלח manually in the browser if needed.")


def submit_day(page: Page, day: _dt.date) -> None:  # pragma: no cover
    try:
        # Use the page's own save routine (posts the modal form via AJAX).
        page.evaluate(config.JS_SAVE_PUNCH)
        # Wait for the modal to close as the success signal.
        try:
            page.locator(config.SELECTORS["punch_modal"]).wait_for(state="hidden", timeout=8000)
            print(f"  Saved {day.isoformat()}.")
        except PWTimeout:
            print(f"  ? Save sent for {day.isoformat()} but modal stayed open; check the browser.")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Could not save {day.isoformat()}: {exc}")
        print("    Click שמירה manually in the browser if needed.")


# ---------------------------------------------------------------------------
# Per-day handlers (return "continue" or "quit")
# ---------------------------------------------------------------------------
def _fill_work_modal(page: Page, day: _dt.date, hours: tuple[str, str, int], tag: str) -> bool:
    start_hhmm, end_hhmm, duration = hours
    print(f"  {tag}: {start_hhmm} - {end_hhmm}  ({duration / 60:.2f}h)")
    return fill_day(page, day, start_hhmm, end_hhmm)


def _handle_work(page: Page, day: _dt.date, label: str, auto_submit: bool = False) -> str:
    print(f"\n{label}  WORK")
    if not _fill_work_modal(page, day, regular_hours(), "hours"):
        if auto_submit:
            print("  Could not auto-fill; skipped.")
            _close_modal(page)
            return "continue"
        if input("  Could not auto-fill. [s]kip / [q]uit / Enter to retry: ").strip().lower() == "q":
            return "quit"
        return "continue"
    if auto_submit:
        print("  Auto-submit enabled; saving.")
        submit_day(page, day)
        return "continue"
    ans = input("  Review in the browser. [Enter]=submit, [s]=skip, [q]=quit: ").strip().lower()
    if ans == "q":
        _close_modal(page)
        return "quit"
    if ans == "s":
        print("  Skipped.")
        _close_modal(page)
        return "continue"
    submit_day(page, day)
    return "continue"


def _handle_erev(
    page: Page,
    day: _dt.date,
    label: str,
    name: str,
    auto_submit: bool = False,
) -> str:
    print(f"\n{label}  EREV {name} (half day)")
    if not _fill_work_modal(page, day, half_hours(), "half-day"):
        if auto_submit:
            print("  Could not auto-fill; skipped.")
            _close_modal(page)
            return "continue"
        if input("  Could not auto-fill. [s]kip / [q]uit / Enter to retry: ").strip().lower() == "q":
            return "quit"
        return "continue"
    if auto_submit:
        print("  Auto-submit enabled; saving half day.")
        submit_day(page, day)
        return "continue"
    ans = input(
        "  [Enter]=submit half day, [f]=full 9-11h instead, [s]=skip, [q]=quit: "
    ).strip().lower()
    if ans == "q":
        _close_modal(page)
        return "quit"
    if ans == "s":
        print("  Skipped.")
        _close_modal(page)
        return "continue"
    if ans == "f":
        _close_modal(page)
        if not _fill_work_modal(page, day, regular_hours(), "full-day"):
            print("  Could not fill full day; skipped.")
            _close_modal(page)
            return "continue"
        if input("  Review. [Enter]=submit, [s]=skip: ").strip().lower() == "s":
            _close_modal(page)
            return "continue"
    submit_day(page, day)
    return "continue"


def _handle_holiday(
    page: Page,
    day: _dt.date,
    label: str,
    name: str,
    auto_submit: bool = False,
) -> str:
    print(f"\n{label}  HOLIDAY: {name}")
    if auto_submit:
        if not fill_holiday(page, day):
            print("  Could not prepare holiday; skipped.")
            _close_modal(page)
            return "continue"
        print("  Auto-submit enabled; reporting holiday.")
        submit_holiday(page, day)
        return "continue"
    ans = input(
        "  [Enter]=report as יום חג, [w]=work hours instead, [s]=skip, [q]=quit: "
    ).strip().lower()
    if ans == "q":
        return "quit"
    if ans == "s":
        print("  Skipped.")
        return "continue"
    if ans == "w":
        if not _fill_work_modal(page, day, regular_hours(), "hours"):
            print("  Could not fill; skipped.")
            _close_modal(page)
            return "continue"
        if input("  Review. [Enter]=submit, [s]=skip: ").strip().lower() == "s":
            _close_modal(page)
            return "continue"
        submit_day(page, day)
        return "continue"
    if not fill_holiday(page, day):
        print("  Could not prepare holiday; skipped.")
        _close_modal(page)
        return "continue"
    if input("  Review the absence in the browser. [Enter]=submit, [s]=skip: ").strip().lower() == "s":
        _close_modal(page)
        return "continue"
    submit_holiday(page, day)
    return "continue"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main() -> None:  # pragma: no cover
    load_dotenv()
    random.seed()

    options = choose_run_options(sys.argv)
    start, end = options.start, options.end
    days = period.target_dates(start, end)

    years = holiday_calendar.years_for(start, end)
    full_hols = holiday_calendar.full_holidays(years)
    erev_hols = holiday_calendar.erev_days(years)

    print(f"Date range: {start.isoformat()} .. {end.isoformat()}")
    print(f"Work days to fill (Sun-Thu): {len(days)}")
    if options.auto_submit:
        print("Auto-submit: enabled (days will be saved without per-day prompts)")
    n_hol = sum(1 for d in days if d in full_hols)
    n_erev = sum(1 for d in days if d not in full_hols and d in erev_hols)
    if n_hol or n_erev:
        print(f"  of which holidays: {n_hol}, erev (half day): {n_erev}")
    if not days:
        print("Nothing to fill.")
        return

    presence_url = config.PRESENCE_URL.format(start=start.isoformat(), end=end.isoformat())

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            headless=config.HEADLESS,
            slow_mo=config.SLOW_MO_MS,
        )
        context.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
        page = context.pages[0] if context.pages else context.new_page()

        ensure_logged_in(page)

        print(f"Opening presence page: {presence_url}")
        page.goto(presence_url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            pass

        for i, day in enumerate(days, 1):
            kind, name = holiday_calendar.classify(day, full_hols, erev_hols)
            label = f"[{i}/{len(days)}] {day.isoformat()} ({day.strftime('%a')})"

            if kind == "holiday":
                action = _handle_holiday(page, day, label, name, options.auto_submit)
            elif kind == "erev":
                action = _handle_erev(page, day, label, name, options.auto_submit)
            else:
                action = _handle_work(page, day, label, options.auto_submit)

            if action == "quit":
                print("Stopping.")
                break

        print("\nDone. Closing browser.")
        if not options.auto_submit:
            input("Press Enter to close the browser window... ")
        context.close()


if __name__ == "__main__":  # pragma: no cover
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
