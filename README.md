# playwright-python-tests

UI tests for [the-internet.herokuapp.com](https://the-internet.herokuapp.com) using Playwright, pytest and a page object model (`pom/`).

The repository also contains [AUT1](#aut1--car-sales-and-rental-app), a local car sales and rental web app to test against.

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

## AUT1 – car sales and rental app

A local application under test in `AUT1/`: an HTML/JS/CSS frontend (`AUT1/fe`) served by a Python backend (`AUT1/be`) with in-memory SQLite databases. It uses only the Python standard library, so there is nothing extra to install.

### Running the server

From the repository root:

```bash
python AUT1/be/server.py
```

Then open <http://127.0.0.1:8000/login_page.html>. Stop the server with `Ctrl+C`.

The databases live in memory and are rebuilt from the SQL scripts on every start, so each run begins with the same seed data and nothing persists between runs. Restart the server after changing a SQL script.

### Options

| Option | Default | Description |
|---|---|---|
| `--host` | `127.0.0.1` | Address to listen on. |
| `--port` | `8000` | Port to listen on. |
| `--front-end-directory` | `AUT1/fe` | Directory with the HTML, JS and CSS files. |
| `--sql-directory` | `AUT1/be/sql` | Directory with `reference/` and `dealership/` subdirectories, each holding `schema.sql` and `seed_data.sql`. Point it at a copy to run with a different data set. |
| `--extra-load`, `-el` | off | Simulates heavy load: every call that touches reference data rolls 3 times, each roll with a ~15% chance of a 2–5 s delay. See [Extra load](#extra-load). |
| `-h`, `--help` | | Prints the options. |

```bash
python AUT1/be/server.py --port 8080
python AUT1/be/server.py --extra-load
python AUT1/be/server.py --sql-directory path/to/test_sql
```

### Users

Only `admin` may use the frontend; the other users exist but get a "not allowed to access the front-end" error on login.

| Username | Password | Frontend access |
|---|---|---|
| `admin` | `admin` | Yes, including **Show whole DB** |
| `superuser` | `superuser` | No |
| `user_vw` | `user_vw` | No |
| `user_tesla` | `user_tesla` | No |
| `viewer` | `viewer` | No |

### Pages

| Page | Content |
|---|---|
| `/login_page.html` | Login form. |
| `/home_page.html` | Welcome message, **Show whole DB** button (admin only), logout. |
| `/database_page.html` | All tables grouped by database, 15 records per page with First / Previous / Next / Last navigation. |

The home and database pages show a footer: *Logged in as **user** on yyyy-mm-dd hh:mm:ss*. Opening them without a session redirects to the login page. Interactive elements carry `data-testid` attributes, for example `login-button`, `show-whole-db-button`, `table-dealership-vehicles`, `row-reference-factories-1`, `pagination-next-dealership-vehicles`, `session-footer`.

### API

| Method and path | Description |
|---|---|
| `POST /api/login` | Body `{"username": ..., "password": ...}`. 401 for wrong credentials, 403 for users not allowed on the frontend. Sets the session cookie. |
| `POST /api/logout` | Ends the session. |
| `GET /api/session` | Logged-in user and `logged_in_at`; 401 when not logged in. |
| `GET /api/database/tables` | First page of every table (admin only). |
| `GET /api/database/tables/<database>/<table>?page=N` | One page of one table, e.g. `/api/database/tables/dealership/vehicles?page=2`. 404 for an unknown table, 400 for an invalid page. |

### Databases

Two in-memory SQLite databases, each built from its own scripts in `AUT1/be/sql/`:

- **REFERENCE** – rarely changing master data: `customers` with the `individual_customers` and `institutional_customers` subtypes, `companies` (banks and leasing companies), `commercial_policy` (fleet size, default fleet discount, default rental prolongation) and `factories`.
- **DEALERSHIP** – `vehicles`, `sale_agreements` / `sales`, `rental_agreements` / `rentals`, `loans`, plus read-only replicas of the REFERENCE tables it references, so all foreign keys are enforced. Writing to a replica directly is rejected; changes go to REFERENCE and are replicated in the same transaction.

### Extra load

With `--extra-load` (`-el`) the server simulates heavy load on reference data: each operation that reads or writes REFERENCE tables, their replicas, or tables displaying replica columns (for example customer names on agreements) rolls 3 times, each with a ~15% chance of a 2–5 s delay. Delays add up, so about 40% of such operations are slowed down and a few take longer than 5 s, at most 15 s. Operations on other tables, login and static files are never delayed, and a delayed reply does not hold up other requests. Each delay is logged:

```text
[extra-load] roll 2/3: delaying reference data reply by 3.4 s
```

Playwright's `expect` assertions time out after 5 s by default, so raise the timeout for runs against a server started with `-el`:

```python
from playwright.sync_api import expect

expect.set_options(timeout=20_000)
```
