import re

import pytest
from playwright.sync_api import expect

from pom import TheInternet
from tests.credentials import Credentials


class TestLogin:
    def test_valid_credentials_open_secure_area(self, the_internet: TheInternet, valid_credentials: Credentials) -> None:
        the_internet.login.open().login(valid_credentials.username, valid_credentials.password)

        expect(the_internet.secure_area.page).to_have_url(re.compile(r"/secure$"))
        expect(the_internet.secure_area.flash_message).to_contain_text("You logged into a secure area!")

    @pytest.mark.parametrize(
        ("username", "password", "expected_message"),
        (
            ("unknown", "SuperSecretPassword!", "Your username is invalid!"),
            ("tomsmith", "wrong-password", "Your password is invalid!"),
        ),
        ids=("invalid-username", "invalid-password"),
    )
    def test_invalid_credentials_show_error(
        self, the_internet: TheInternet, username: str, password: str, expected_message: str
    ) -> None:
        the_internet.login.open().login(username, password)

        expect(the_internet.login.page).to_have_url(re.compile(r"/login$"))
        expect(the_internet.login.flash_message).to_contain_text(expected_message)

    def test_logout_returns_to_login_page(self, the_internet: TheInternet, valid_credentials: Credentials) -> None:
        the_internet.login.open().login(valid_credentials.username, valid_credentials.password)
        the_internet.secure_area.logout()

        expect(the_internet.login.page).to_have_url(re.compile(r"/login$"))
        expect(the_internet.login.flash_message).to_contain_text("You logged out of the secure area!")
