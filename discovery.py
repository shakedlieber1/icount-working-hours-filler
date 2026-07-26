"""Phase 1: discovery / inspection run.

Logs into icount with credentials from .env, opens the presence page for the
current pay period, and dumps artifacts (screenshot, HTML, and a printed report
of candidate inputs/buttons/day-rows) so we can pick stable selectors for the
fill automation. It SUBMITS NOTHING. It ends in the Playwright Inspector so you
can hover/click elements and copy their selectors.

Run:  python discovery.py
"""

from __future__ import annotations

import os
import pathlib

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

import config
import period

OUT_DIR = pathlib.Path("discovery_output")


def _maybe_fill(page, selector: str, value: str) -> bool:
    """Fill the first matching, visible element. Returns True if filled."""
    if not value:
        return False
    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=5000)
        loc.fill(value)
        return True
    except PWTimeout:
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"  ! could not fill {selector!r}: {exc}")
        return False


def login(page) -> None:
    user = os.environ.get("ICOUNT_USER", "")
    passwd = os.environ.get("ICOUNT_PASS", "")
    company = os.environ.get("ICOUNT_COMPANY", "")

    if not user or not passwd:
        print("! ICOUNT_USER / ICOUNT_PASS missing in .env - you can log in by hand in the open window.")

    print(f"-> Opening login page: {config.LOGIN_URL}")
    page.goto(config.LOGIN_URL, wait_until="domcontentloaded")

    # icount may show a passkey screen first; switch to password login if so.
    try:
        chooser = page.locator(config.SELECTORS["passkey_password_chooser"]).first
        if chooser.is_visible(timeout=3000):
            chooser.click()
            print("   switched to password login")
    except Exception:  # noqa: BLE001
        pass

    filled_company = _maybe_fill(page, config.SELECTORS["login_company"], company)
    filled_user = _maybe_fill(page, config.SELECTORS["login_user"], user)
    filled_pass = _maybe_fill(page, config.SELECTORS["login_pass"], passwd)
    print(f"   filled company={filled_company} user={filled_user} pass={filled_pass}")

    if filled_user and filled_pass:
        try:
            page.locator(config.SELECTORS["login_submit"]).first.click(timeout=5000)
            print("   submitted login form")
        except Exception as exc:  # noqa: BLE001
            print(f"   ! could not click submit ({exc}). Please submit manually in the window.")

    print("\n   If a captcha / OTP / extra step appears, complete it in the browser window now.")
    input("   Press Enter here once you are fully logged in... ")


def report_candidates(page) -> None:
    """Print candidate form elements to help choose selectors."""
    print("\n=== Candidate inputs ===")
    inputs = page.eval_on_selector_all(
        "input, select, textarea",
        """els => els.map(e => ({
            tag: e.tagName.toLowerCase(),
            type: e.getAttribute('type'),
            name: e.getAttribute('name'),
            id: e.id,
            placeholder: e.getAttribute('placeholder'),
            cls: e.getAttribute('class'),
        }))""",
    )
    for i, el in enumerate(inputs):
        print(f"  [{i}] {el}")

    print("\n=== Candidate buttons / clickables ===")
    buttons = page.eval_on_selector_all(
        "button, a[role=button], input[type=submit], input[type=button], [onclick]",
        """els => els.slice(0, 80).map(e => ({
            tag: e.tagName.toLowerCase(),
            text: (e.innerText || e.value || '').trim().slice(0, 40),
            id: e.id,
            cls: e.getAttribute('class'),
        }))""",
    )
    for i, el in enumerate(buttons):
        print(f"  [{i}] {el}")

    print("\n=== Elements with data-date / data-day attributes (likely day rows) ===")
    rows = page.eval_on_selector_all(
        "[data-date], [data-day]",
        """els => els.slice(0, 60).map(e => ({
            tag: e.tagName.toLowerCase(),
            dataDate: e.getAttribute('data-date'),
            dataDay: e.getAttribute('data-day'),
            cls: e.getAttribute('class'),
        }))""",
    )
    if rows:
        for i, el in enumerate(rows):
            print(f"  [{i}] {el}")
    else:
        print("  (none found - day rows may use a different structure; inspect manually)")


def main() -> None:
    load_dotenv()
    OUT_DIR.mkdir(exist_ok=True)

    start, end = period.compute_period()
    presence_url = config.PRESENCE_URL.format(start=start.isoformat(), end=end.isoformat())
    print(f"Pay period: {start.isoformat()} .. {end.isoformat()}")
    print(f"Presence URL: {presence_url}\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            headless=config.HEADLESS,
            slow_mo=config.SLOW_MO_MS,
        )
        context.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
        page = context.pages[0] if context.pages else context.new_page()

        login(page)

        print(f"\n-> Opening presence page: {presence_url}")
        page.goto(presence_url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            pass

        # Artifacts
        shot = OUT_DIR / "presence.png"
        html = OUT_DIR / "presence.html"
        page.screenshot(path=str(shot), full_page=True)
        html.write_text(page.content(), encoding="utf-8")
        print(f"\nSaved screenshot -> {shot}")
        print(f"Saved HTML       -> {html}")

        report_candidates(page)

        print(
            "\n=== Playwright Inspector ===\n"
            "The Inspector window is open. Hover/click elements in the page to copy\n"
            "their selectors, then paste the good ones into config.py SELECTORS.\n"
            "Close the Inspector (or press Resume) when done.\n"
        )
        page.pause()

        context.close()


if __name__ == "__main__":
    main()
