import os
import urllib.error
import urllib.request

import pytest
from playwright.sync_api import Page

from pom import Aut1Application, Aut1VehiclesPage
from tests.aut1_seeded_users import Aut1SeededUsers


class Aut1ServerProbe:
    def __init__(self, base_url: str, probed_path: str, timeout_seconds: float) -> None:
        self.base_url = base_url
        self.probed_path = probed_path
        self.timeout_seconds = timeout_seconds

    def is_reachable(self) -> bool:
        try:
            with urllib.request.urlopen(self.base_url.rstrip("/") + self.probed_path, timeout=self.timeout_seconds):
                return True
        except (urllib.error.URLError, OSError):
            return False


@pytest.fixture(scope="session")
def aut1_base_url() -> str:
    return os.environ.get("AUT1_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session", autouse=True)
def require_running_aut1_server(aut1_base_url: str) -> None:
    if not Aut1ServerProbe(aut1_base_url, "/login_page.html", timeout_seconds=3).is_reachable():
        pytest.fail(f"AUT1 is not reachable at {aut1_base_url}; start it first with: python AUT1/be/server.py", pytrace=False)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict, aut1_base_url: str) -> dict:
    return {**browser_context_args, "base_url": aut1_base_url, "viewport": {"width": 1600, "height": 2000}}


@pytest.fixture(scope="session")
def aut1_users() -> Aut1SeededUsers:
    return Aut1SeededUsers()


@pytest.fixture
def aut1(page: Page) -> Aut1Application:
    return Aut1Application(page)


@pytest.fixture
def dealer_vehicles_page(aut1: Aut1Application, aut1_users: Aut1SeededUsers) -> Aut1VehiclesPage:
    return aut1.open_vehicles_page_as(aut1_users.dealer.username, aut1_users.dealer.password)
