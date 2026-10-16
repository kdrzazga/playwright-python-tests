import os

import pytest
from playwright.sync_api import Page

from pom import Aut1UserInterface, Aut1VehiclesPage
from tests.aut1_seeded_users import Aut1SeededUsers
from tests.compact_number_format import CompactEnglishNumberFormat
from tests.eventual_assertion import EventualAssertion


@pytest.fixture(scope="session")
def aut1_base_url() -> str:
    return os.environ.get("AUT1_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict, aut1_base_url: str) -> dict:
    return {**browser_context_args, "base_url": aut1_base_url, "viewport": {"width": 1600, "height": 2000}}


@pytest.fixture(scope="session")
def aut1_users() -> Aut1SeededUsers:
    return Aut1SeededUsers()


@pytest.fixture(scope="session")
def compact_number_format() -> CompactEnglishNumberFormat:
    return CompactEnglishNumberFormat()


@pytest.fixture
def eventually(page: Page) -> EventualAssertion:
    return EventualAssertion(page, timeout_ms=10_000, poll_interval_ms=200)


@pytest.fixture
def aut1_ui(page: Page) -> Aut1UserInterface:
    return Aut1UserInterface(page)


@pytest.fixture
def dealer_vehicles_page(aut1_ui: Aut1UserInterface, aut1_users: Aut1SeededUsers) -> Aut1VehiclesPage:
    return aut1_ui.go_to_vehicles_page_as(aut1_users.dealer.username, aut1_users.dealer.password)
