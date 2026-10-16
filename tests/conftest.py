import pytest
from playwright.sync_api import expect


@pytest.fixture(scope="session", autouse=True)
def configure_expect_timeout() -> None:
    expect.set_options(timeout=10_000)
