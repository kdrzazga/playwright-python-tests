# playwright-python-tests

UI tests for [the-internet.herokuapp.com](https://the-internet.herokuapp.com) using Playwright, pytest and a page object model (`pom/`).

The repository also contains two local applications to test against: [AUT1](#aut1--car-sales-and-rental-app), a car sales and rental web app, and [AUT2](#aut2--dealership-analytics-dash), a Dash analytics dashboard over the same data.

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
| `--sql-directory` | `AUT1/be/sql` | Directory with `reference/`, `dealership/` and `security/` subdirectories, each holding `schema.sql` and `seed_data.sql`. Point it at a copy to run with a different data set. |
| `--extra-load`, `-el` | off | Simulates heavy load: every call that touches reference data rolls 3 times, each roll with a ~15% chance of a 2–5 s delay. See [Extra load](#extra-load). |
| `-h`, `--help` | | Prints the options. |

```bash
python AUT1/be/server.py --port 8080
python AUT1/be/server.py --extra-load
python AUT1/be/server.py --sql-directory path/to/test_sql
```

### Users

Users, permissions and grants live in the SECURITY database (passwords stored as salted PBKDF2 hashes). Logging in to the frontend requires the `frontend.access` permission; what each user sees there follows from their other permissions.

| Username | Password | Role | Permissions | Frontend |
|---|---|---|---|---|
| `admin` | `admin` | admin | all except `vehicle.add` (23), including `view_db_tables` | yes |
| `superuser` | `superuser` | superuser | all except `view_db_tables` (23) | yes |
| `dealer_tesla_vw` | `dealer_tesla_vw` | dealer | the four `*.view` permissions, `vehicle.add`, `vehicle.remove`, `brand.tesla.access`, `brand.vw.access`, `frontend.access` (9) | yes |
| `viewer` | `viewer` | viewer | the four `*.view` permissions, all six brands and `frontend.access` (11) | yes |
| `user_vw` | `user_vw` | viewer | the four `*.view` permissions, `brand.vw.access` and `frontend.access` (6) | yes |
| `obsolete_vw` | `obsolete_vw` | viewer | `vehicle.view` and `brand.vw.access` (2) | no: correct credentials get 403 |

Available permissions: `frontend.access`; `view_db_tables`; `vehicle.*`, `rental.*`, `sell.*` and `loan.*`, each with `view`, `add`, `modify` and `remove`; one `brand.<code>.access` per brand: `vw`, `toyota`, `mercedes`, `tesla`, `skoda`, `bmw`.

What each role may hold is data in `security.role_permission_rules` (`LIKE` patterns) and enforced by triggers:

| Role | Allowed permissions |
|---|---|
| `admin` | everything except `vehicle.add` |
| `superuser` | everything except `view_db_tables` |
| `dealer` | `vehicle.*`, `rental.*`, `sell.*`, `loan.view`, `brand.*.access`, `frontend.access` |
| `viewer` | `*.view`, `brand.*.access`, `frontend.access` |

Granting a disallowed permission, changing a user's role while they hold permissions the new role does not allow, or deleting a rule that existing grants depend on is rejected.

**Brand access.** Every vehicle action needs both the action permission and access to the vehicle's brand. Vehicles of other brands are invisible to the user: they are left out of lists, and removing one answers 404 as if it did not exist. Adding a vehicle of a brand the user cannot access answers 403. The checks run in the backend, so they also apply to direct API calls.

### Pages

| Page | Content |
|---|---|
| `/login_page.html` | Login form. |
| `/home_page.html` | Welcome message, **Show whole DB** button (needs `view_db_tables`), **Vehicles** button (needs `vehicle.view`), logout. |
| `/vehicles_page.html` | Vehicles of the brands the user can access, 15 per page. **Remove** buttons with `vehicle.remove`; an **Add vehicle** form with `vehicle.add` (brand choices limited to accessible brands). |
| `/database_page.html` | All tables grouped by database, 15 records per page with First / Previous / Next / Last navigation. |

The home, database and vehicles pages show a footer: *Logged in as **user** on yyyy-mm-dd hh:mm:ss*. Opening them without a session redirects to the login page. Interactive elements carry `data-testid` attributes, for example `login-button`, `show-whole-db-button`, `table-dealership-vehicles`, `row-reference-factories-1`, `pagination-next-dealership-vehicles`, `session-footer`, `vehicles-button`, `vehicle-row-16`, `remove-vehicle-16`, `vehicle-field-brand`, `add-vehicle-button`, `vehicle-status-message`, `vehicle-error-message`.

### API

| Method and path | Description |
|---|---|
| `POST /api/login` | Body `{"username": ..., "password": ...}`. 401 for wrong credentials, 403 for users without `frontend.access` (e.g. `obsolete_vw`). Sets the session cookie. |
| `POST /api/logout` | Ends the session. |
| `GET /api/session` | Logged-in user and `logged_in_at`; 401 when not logged in. |
| `GET /api/database/tables` | First page of every table (needs `view_db_tables`). |
| `GET /api/database/tables/<database>/<table>?page=N` | One page of one table, e.g. `/api/database/tables/dealership/vehicles?page=2`. 404 for an unknown table, 400 for an invalid page. |
| `GET /api/vehicles?page=N` | One page of vehicles of the user's accessible brands (needs `vehicle.view`). |
| `GET /api/vehicles/form-options` | Accessible brands and allowed values for the add form (needs `vehicle.add`). |
| `POST /api/vehicles` | Adds a vehicle from a JSON object with all vehicle fields; `registration` is optional. 201 on success, 400 for invalid data, 403 without `vehicle.add` or brand access. |
| `DELETE /api/vehicles/<id>` | Removes a vehicle (needs `vehicle.remove`). 404 if it does not exist or its brand is not accessible, 409 if it is part of a sale or rental. |

### Databases

Three in-memory SQLite databases, each built from its own scripts in `AUT1/be/sql/`:

- **REFERENCE** – rarely changing master data: `customers` with the `individual_customers` and `institutional_customers` subtypes, `companies` (banks and leasing companies), `commercial_policy` (fleet size, default fleet discount, default rental prolongation), `factories` and `brands`.
- **DEALERSHIP** – `vehicles` (`brand` references `brands`), `sale_agreements` / `sales`, `rental_agreements` / `rentals`, `loans`, plus read-only replicas of the REFERENCE tables it references, so all foreign keys are enforced. Writing to a replica directly is rejected; changes go to REFERENCE and are replicated in the same transaction.
- **SECURITY** – `users` (password hashes are hidden on the database page), `permissions` (brand permissions reference `brands`), `role_permission_rules`, `user_permission`, and read-only replicas of `companies` and `brands` so `users.company_id` and `permissions.brand_id` have enforced foreign keys.

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

## AUT2 – dealership analytics (Dash)

A [Dash](https://dash.plotly.com/) dashboard in `AUT2/` that analyses the AUT1 dealership data. It builds its own in-memory copy of the AUT1 databases from the same SQL scripts at startup, using AUT1's data layer, so both apps start from identical data. Changes made in a running AUT1 are not visible in AUT2.

### Setup

AUT2 needs Dash (which brings Flask and Plotly), unlike AUT1:

```bash
venv/Scripts/python -m pip install -r AUT2/requirements.txt
```

### Running the dashboard

```bash
venv/Scripts/python AUT2/app.py
```

Then open <http://127.0.0.1:8050/>.

| Option | Default | Description |
|---|---|---|
| `--host` | `127.0.0.1` | Address to listen on. |
| `--port` | `8050` | Port to listen on. |
| `--aut1-backend-directory` | `AUT1/be` | AUT1 backend whose data layer builds the database. |
| `--aut1-sql-directory` | `AUT1/be/sql` | AUT1 SQL scripts to load. |
| `--as-of-date` | today | Date (`YYYY-MM-DD`) used for vehicle status (available / rented / sold) and as the default end of date ranges. Fix it in tests so results do not change from day to day. |
| `--debug` | off | Dash debug mode with hot reload and the in-page error overlay. |

### Tabs

| Tab | Content |
|---|---|
| Overview | Brand checklist, **All brands** button and agreement date range; key figure cards; vehicles sold and rented per month; sales revenue by brand. Clicking a revenue bar narrows the brand checklist to that brand. |
| Stock | Brand, engine and status filters; vehicles-by-status donut; a sortable, filterable vehicle table (15 rows per page). |
| Loans | Loan status filter; financed principal by lender; loans table with instalments and total interest. |
| Factories | Factory state and country filters; a year slider; a world map of factories operating in the selected year (green: still active, red: closed since); factories operating per year; clicking a map marker shows the factory's details. |

Interactive Dash components have stable `id`s (for example `#overview-brand-checklist`, `#revenue-by-brand-graph`, `#stock-table`, `#factory-year-slider`, `#factory-map-graph`); containers carry `data-testid` attributes (for example `key-figure-vehicles_sold`, `stock-vehicle-count`, `factory-count`, `factory-detail-panel`, `factory-detail-name`).

Every filter change is a round trip to the server, so wait for the updated content (for example the `factory-count` text) rather than asserting immediately after an interaction.
