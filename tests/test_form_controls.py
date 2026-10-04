import pytest
from playwright.sync_api import expect

from pom import TheInternet


pytestmark = pytest.mark.forms


class TestCheckboxes:
    @pytest.mark.smoke
    def test_initial_state(self, the_internet: TheInternet) -> None:
        checkboxes = the_internet.checkboxes.open()

        expect(checkboxes.checkboxes).to_have_count(2)
        expect(checkboxes.checkbox(0)).not_to_be_checked()
        expect(checkboxes.checkbox(1)).to_be_checked()

    def test_toggle_checkboxes(self, the_internet: TheInternet) -> None:
        checkboxes = the_internet.checkboxes.open()

        checkboxes.check(0)
        checkboxes.uncheck(1)

        expect(checkboxes.checkbox(0)).to_be_checked()
        expect(checkboxes.checkbox(1)).not_to_be_checked()


class TestDropdown:
    def test_select_option(self, the_internet: TheInternet) -> None:
        dropdown = the_internet.dropdown.open()

        dropdown.select_option("Option 2")

        expect(dropdown.dropdown).to_have_value("2")


class TestAddRemoveElements:
    def test_add_elements(self, the_internet: TheInternet) -> None:
        add_remove_elements = the_internet.add_remove_elements.open()

        add_remove_elements.add_elements(3)

        expect(add_remove_elements.delete_buttons).to_have_count(3)

    def test_remove_element(self, the_internet: TheInternet) -> None:
        add_remove_elements = the_internet.add_remove_elements.open()

        add_remove_elements.add_elements(2)
        add_remove_elements.remove_element()

        expect(add_remove_elements.delete_buttons).to_have_count(1)
