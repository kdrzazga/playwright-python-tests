import re

import pytest
from playwright.sync_api import expect

from pom import Aut1Application, Aut1VehiclesPage
from tests.aut1_seeded_users import Aut1SeededUsers


pytestmark = pytest.mark.aut1


class TestAut1Access:
    @pytest.mark.auth
    @pytest.mark.negative
    def test_user_without_frontend_access_is_refused_at_login(self, aut1: Aut1Application, aut1_users: Aut1SeededUsers) -> None:
        refused_user = aut1_users.user_without_frontend_access

        aut1.login_page.open().log_in(refused_user.username, refused_user.password)

        expect(aut1.login_page.error_message).to_be_visible()
        expect(aut1.login_page.error_message).to_have_text(re.compile(r"\S"))
        expect(aut1.page).to_have_url(re.compile(r"/login_page\.html$"))

    @pytest.mark.vehicles
    @pytest.mark.smoke
    def test_dealer_sees_only_vehicles_of_accessible_brands(self, dealer_vehicles_page: Aut1VehiclesPage, aut1_users: Aut1SeededUsers) -> None:
        expected_brand_names = aut1_users.dealer_accessible_brand_names

        listed_brand_names = {vehicle_row.cell("brand") for vehicle_row in dealer_vehicles_page.vehicle_table.read_all_rows()}

        assert tuple(dealer_vehicles_page.read_accessible_brand_names()) == expected_brand_names
        assert listed_brand_names, "the dealer should see at least one vehicle"
        assert listed_brand_names <= set(expected_brand_names)
