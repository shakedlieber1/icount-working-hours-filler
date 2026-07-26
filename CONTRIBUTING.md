# Contributing

Thanks for helping improve iCount Working-Hours Filler.

## Ground Rules

- Keep user credentials, browser profiles, screenshots, and HTML dumps out of commits.
- Prefer small, focused pull requests.
- Preserve manual review as the default workflow. Automatic submission must stay behind the explicit `--auto-submit` flag.
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

Run the unit tests and a basic syntax check before opening a pull request:

```bash
.venv/bin/python -m unittest
.venv/bin/python -m coverage run -m unittest
.venv/bin/python -m coverage report
.venv/bin/python -m compileall -q .
```

If you changed browser automation behavior, manually test against a non-critical date range and verify that manual mode still waits for explicit confirmation. If you changed automatic submission, test `--auto-submit` against a safe range too.

## Commit Messages and Releases

Releases are created automatically in GitHub from conventional commits merged
to `main` or `master`.

- Use `fix:` for patch releases.
- Use `feat:` for minor releases.
- Use `BREAKING CHANGE:` in the commit body, or `!` in the commit type, for
  major releases.

Commits such as `docs:`, `test:`, `ci:`, and `chore:` do not create a release
unless they include a breaking change.

## Pull Request Checklist

- No credentials, cookies, browser profiles, screenshots, or discovery HTML are included.
- README or setup docs are updated when behavior changes.
- Risky automation changes include a note explaining how they were tested.
- The project still works with Python 3.12.
