# playwright-python-tests

UI tests for [the-internet.herokuapp.com](https://the-internet.herokuapp.com) using Playwright, pytest and a page object model (`pom/`).

## Setup

Requires Python 3.14.

```bash
python -m venv venv
venv/Scripts/python -m pip install -r requirements.txt
venv/Scripts/python -m playwright install
```

Run pytest through the venv (`venv/Scripts/python -m pytest`) or activate the venv first — a `pytest` from another Python install won't see the project's plugins.

## Running tests

```bash
venv/Scripts/python -m pytest
venv/Scripts/python -m pytest --browser webkit
venv/Scripts/python -m pytest tests/test_login.py
```

Default options live in `pyproject.toml`: failed tests are retried twice (`--reruns 2`), and screenshots, videos and traces of failures are saved to `test-results/`.

### Verbose run (watch the browser)

Tests run headless by default. To see the browser and follow each click:

```bash
# Visible browser, actions slowed down by 500 ms so they're easy to follow
venv/Scripts/python -m pytest --headed --slowmo 500 -v

# Same, for a single test
venv/Scripts/python -m pytest "tests/test_login.py::TestLogin::test_valid_credentials_open_secure_area" --headed --slowmo 500 -v
```

- `--headed` opens a visible browser window.
- `--slowmo <ms>` pauses before each Playwright action (click, fill, navigation).
- `-v` prints each test name and result; add `-s` to also show `print()` output.
- Retries are on by default, so a failing test replays up to three times; add `--reruns 0` while watching.

To step through actions one at a time, use the Playwright Inspector:

```bash
PWDEBUG=1 venv/Scripts/python -m pytest -m smoke --headed
```

In PowerShell, set the variable first: `$env:PWDEBUG = "1"`, then run pytest. Remove it afterwards with `Remove-Item Env:PWDEBUG`.

To replay a failure after the fact, open its saved trace in the trace viewer:

```bash
venv/Scripts/python -m playwright show-trace test-results/<test-folder>/trace.zip
```

Login credentials default to the public demo account; override them with the `THE_INTERNET_USERNAME` and `THE_INTERNET_PASSWORD` environment variables.

## Tags

Tests are tagged with pytest markers so you can run a subset with `-m`.

### Feature area

Every test has exactly one area tag.

| Tag | Covers |
|---|---|
| `home` | Home page and navigation (`test_home.py`) |
| `auth` | Login and logout (`test_login.py`) |
| `forms` | Checkboxes, dropdown, add/remove elements (`test_form_controls.py`) |
| `alerts` | JavaScript alert, confirm and prompt dialogs |
| `dynamic_loading` | Content rendered after an async load |

### Test type

| Tag | Meaning |
|---|---|
| `smoke` | Fast critical-path checks, one per feature area |
| `negative` | Invalid input / error-path scenarios |
| `slow` | Waits on deliberately delayed page behaviour |

### Selecting tests

```bash
# Smoke suite only
venv/Scripts/python -m pytest -m smoke

# One feature area
venv/Scripts/python -m pytest -m auth

# Combine with and / or / not
venv/Scripts/python -m pytest -m "auth and not negative"
venv/Scripts/python -m pytest -m "alerts or forms"
venv/Scripts/python -m pytest -m "not slow"

# Preview which tests a selection matches, without running them
venv/Scripts/python -m pytest -m smoke --collect-only -q

# List all registered tags
venv/Scripts/python -m pytest --markers
```

### Adding a tag

Markers are registered under `[tool.pytest.ini_options] markers` in `pyproject.toml`. Because `--strict-markers` is enabled, an unregistered or misspelled tag fails the run, so register a new tag there before using it.

- Tag a whole file with `pytestmark = pytest.mark.<area>` at module level.
- Tag a class or a single test with the `@pytest.mark.<tag>` decorator.
