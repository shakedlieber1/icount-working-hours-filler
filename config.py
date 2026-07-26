"""Central configuration for the icount presence automation.

Selectors are intentionally kept in one place. After running discovery.py
(Phase 1), update the SELECTORS values to match the real icount UI.
Each selector is a Playwright selector string (CSS, text=, role=, xpath=, etc.).
"""

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
BASE_URL = "https://app.icount.co.il"
LOGIN_URL = "https://app.icount.co.il/login.php"
# The presence page. {start} and {end} are filled with YYYY-MM-DD at runtime.
PRESENCE_URL = "https://app.icount.co.il/presence/?start_date={start}&end_date={end}#"

# ---------------------------------------------------------------------------
# Browser behaviour
# ---------------------------------------------------------------------------
HEADLESS = False        # always run visible so you can watch/confirm each step
SLOW_MO_MS = 400        # delay between actions (ms) so steps are watchable
DEFAULT_TIMEOUT_MS = 30000

# Persisted browser profile so the login session is reused between runs.
USER_DATA_DIR = ".auth"

# ---------------------------------------------------------------------------
# Hours generation
# ---------------------------------------------------------------------------
# Start time window (minutes from midnight). 08:00 = 480, 10:00 = 600.
START_MIN_MINUTES = 8 * 60
START_MAX_MINUTES = 10 * 60
# Regular daily duration window (minutes). 9h = 540, 10h = 600. Floor 8h.
DURATION_MIN_MINUTES = 9 * 60
DURATION_MAX_MINUTES = 11 * 60
MIN_DURATION_MINUTES = 8 * 60  # hard floor enforced regardless of the above

# Erev-chag (shortened) duration window. 4h = 240, 7h = 420.
HALF_DURATION_MIN_MINUTES = 4 * 60
HALF_DURATION_MAX_MINUTES = 7 * 60

# Which weekdays to fill. Python date.weekday(): Mon=0 .. Sun=6.
# Israeli work week Sunday-Thursday => {6, 0, 1, 2, 3}.
WORK_WEEKDAYS = {6, 0, 1, 2, 3}

# ---------------------------------------------------------------------------
# Holidays
# ---------------------------------------------------------------------------
# Categories from the `holidays` library to treat as full days off.
# PUBLIC = Jewish Yom Tov + civil Independence Day. Add OPTIONAL/SCHOOL here to
# include Memorial Day, Purim, Chol HaMoed, etc.
from holidays.constants import PUBLIC  # noqa: E402

HOLIDAY_CATEGORIES = (PUBLIC,)
# icount day type to use when reporting a holiday as an absence day.
HOLIDAY_DAY_TYPE_ID = "12"  # יום חג

# ---------------------------------------------------------------------------
# Selectors  (PLACEHOLDERS - confirm/replace using discovery.py output)
# ---------------------------------------------------------------------------
SELECTORS = {
    # --- Login (confirmed against login.php) ---
    # icount may first show a passkey screen; click this to switch to password login.
    "passkey_password_chooser": "#passkey_chooser_password_link",
    "login_user": "#username",
    "login_pass": "#password",
    "login_company": "#compidentifier",
    "login_submit": "#login-button",
    # 2FA (only appears if your account has it enabled) - completed manually.
    "twofa_code": "#2fa_code",
    "twofa_submit": "#2fa-button",
    # An element that is only present once logged in (used to confirm login).
    "logged_in_marker": "text=נוכחות",

    # --- Add-work-day modal (#punch_modal), confirmed against the presence page ---
    # The modal container that appears when adding a work day.
    "punch_modal": "#punch_modal",
    # Visible date/time inputs inside the modal.
    "punch_start_date": "#punch_modal_start_date",
    "punch_start_time": "#punch_modal_start_time",
    "punch_end_date": "#punch_modal_end_date",
    "punch_end_time": "#punch_modal_end_time",
    # Hidden ISO date fields the form actually submits.
    "punch_iso_start_date": "#iso-punch_modal_start_date",
    "punch_iso_end_date": "#iso-punch_modal_end_date",
    # Day type select (leave empty for a normal work day).
    "punch_day_type": "#punch_modal_day_type_id",
    # Save button inside the modal.
    "punch_save": "#punch_modal .btn-success",

    # --- Absence / holiday modal (#special_day_modal_new) ---
    "special_day_modal": "#special_day_modal_new",
    "special_day_in_date": "#special_day_in_date",
    "special_day_out_date": "#special_day_out_date",
    "special_day_iso_in": "#iso-special_day_in_date",
    "special_day_iso_out": "#iso-special_day_out_date",
    "special_day_type": "#special_day_type_id",
    "special_day_save": "#special_day_modal_new .save_special_day",
}

# JS the page already defines. We call these directly for reliability.
# open_punch_modal('create', 'YYYY-MM-DD') opens the add modal pre-set to a date.
JS_OPEN_PUNCH_MODAL = "(d) => open_punch_modal('create', d)"
# punch_modal_save() posts the form via the page's own AJAX.
JS_SAVE_PUNCH = "() => punch_modal_save()"
# Opens the "report absence day" modal used for holidays.
JS_OPEN_SPECIAL_DAY = "() => punchClock.modals.special_day.open()"
