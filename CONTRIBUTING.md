# Contributing

Thanks for helping improve iCount Working-Hours Filler.

## Ground Rules

- Keep user credentials, browser profiles, screenshots, and HTML dumps out of commits.
- Prefer small, focused pull requests.
- Preserve the manual review-before-submit workflow. The tool should not save work days without a user confirmation.
- Avoid logging secrets, cookies, session data, or full page HTML from authenticated iCount pages.

## Local Setup

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
cp .env.example .env
```

Fill `.env` with your own iCount credentials before running the app locally.

## Development Checks

Run a basic syntax check before opening a pull request:

```bash
.venv/bin/python -m compileall -q .
```

If you changed browser automation behavior, manually test against a non-critical pay period and verify that every save still waits for explicit confirmation.

## Pull Request Checklist

- No credentials, cookies, browser profiles, screenshots, or discovery HTML are included.
- README or setup docs are updated when behavior changes.
- Risky automation changes include a note explaining how they were tested.
- The project still works with Python 3.12.
