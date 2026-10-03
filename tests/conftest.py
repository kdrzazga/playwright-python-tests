import os

import pytest
from playwright.sync_api import Page, expect

from pom import TheInternet
from tests.credentials import Credentials


@pytest.fixture(scope="session", autouse=True)
def configure_expect_timeout() -> None:
    expect.set_options(timeout=10_000)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    return {**browser_context_args, "viewport": {"width": 1280, "height": 720}}


@pytest.fixture(scope="session")
def valid_credentials() -> Credentials:
    return Credentials(
        username=os.environ.get("THE_INTERNET_USERNAME", "tomsmith"),
        password=os.environ.get("THE_INTERNET_PASSWORD", "SuperSecretPassword!"),
    )


@pytest.fixture
def the_internet(page: Page) -> TheInternet:
    return TheInternet(page)
