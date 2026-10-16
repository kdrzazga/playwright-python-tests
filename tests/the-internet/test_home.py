import re

import pytest
from playwright.sync_api import expect

from pom import TheInternet


pytestmark = pytest.mark.home


class TestHomePage:
    @pytest.mark.smoke
    def test_displays_welcome_heading(self, the_internet: TheInternet) -> None:
        the_internet.home.open()

        expect(the_internet.home.heading).to_have_text("Welcome to the-internet")

    def test_lists_examples(self, the_internet: TheInternet) -> None:
        the_internet.home.open()

        expect(the_internet.home.example_link("Form Authentication")).to_be_visible()
        expect(the_internet.home.example_links).not_to_have_count(0)

    def test_navigates_to_form_authentication(self, the_internet: TheInternet) -> None:
        the_internet.home.open().go_to_example("Form Authentication")

        expect(the_internet.login.page).to_have_url(re.compile(r"/login$"))
        expect(the_internet.login.heading).to_have_text("Login Page")
