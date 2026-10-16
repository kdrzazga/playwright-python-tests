import re
from dataclasses import dataclass
from typing import Self

from playwright.sync_api import Locator, Page, expect


@dataclass(frozen=True)
class VehicleRow:
    vehicle_id: str
    cells_by_column_name: dict[str, str]

    def cell(self, column_name: str) -> str:
        return self.cells_by_column_name[column_name]


class Aut1BasePage:
    def __init__(self, page: Page, path: str) -> None:
        self.page = page
        self.path = path

    def open(self) -> Self:
        self.page.goto(self.path)
        return self


class Aut1LoginPage(Aut1BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/login_page.html")
        self.username_input = page.get_by_test_id("username-input")
        self.password_input = page.get_by_test_id("password-input")
        self.login_button = page.get_by_test_id("login-button")
        self.error_message = page.get_by_test_id("login-error-message")

    def log_in(self, username: str, password: str) -> None:
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()


class Aut1HomePage(Aut1BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/home_page.html")
        self.welcome_message = page.get_by_test_id("welcome-message")
        self.vehicles_button = page.get_by_test_id("vehicles-button")


class VehicleTable:
    def __init__(self, page: Page) -> None:
        self.table = page.get_by_test_id("vehicles-table")
        self.header_cells = self.table.locator("thead th")
        self.rows = self.table.locator("tbody tr")
        self.row_test_id_prefix = "vehicle-row-"

    def row(self, row_index: int) -> Locator:
        return self.rows.nth(row_index)

    def read_row(self, row_index: int) -> VehicleRow:
        return self._read_row_element(self.row(row_index))

    def read_all_rows(self) -> list[VehicleRow]:
        return [self._read_row_element(row_element) for row_element in self.rows.all()]

    def _read_row_element(self, row_element: Locator) -> VehicleRow:
        column_names = [header_text.strip() for header_text in self.header_cells.all_text_contents()]
        cell_texts = [cell_text.strip() for cell_text in row_element.locator("td").all_text_contents()]
        vehicle_id = row_element.get_attribute("data-testid").removeprefix(self.row_test_id_prefix)
        return VehicleRow(vehicle_id=vehicle_id, cells_by_column_name=dict(zip(column_names, cell_texts)))


class VehicleBarChart:
    def __init__(self, page: Page, test_id_prefix: str, charted_value_attribute_name: str) -> None:
        self.page = page
        self.test_id_prefix = test_id_prefix
        self.charted_value_attribute_name = charted_value_attribute_name
        self.container = page.get_by_test_id(f"{test_id_prefix}-bar-chart")
        self.bars = page.get_by_test_id(f"{test_id_prefix}-chart-bars").locator("g.chart-bar")
        self.empty_chart_hint = page.get_by_test_id(f"{test_id_prefix}-chart-empty-hint")
        self.x_axis_title = page.get_by_test_id(f"{test_id_prefix}-chart-x-axis-title")
        self.y_axis_title = page.get_by_test_id(f"{test_id_prefix}-chart-y-axis-title")
        self.horizontal_fraction_before_all_bars = 0.03
        self.horizontal_fraction_after_all_bars = 0.97

    def bar_of_vehicle(self, vehicle_id: str) -> Locator:
        return self.page.get_by_test_id(f"{self.test_id_prefix}-bar-{vehicle_id}")

    def bar_at_display_position(self, display_position: int) -> Locator:
        return self.bars.nth(display_position)

    def drop_vehicle_row_before_all_bars(self, vehicle_row: Locator) -> None:
        self.receive_dragged_element(vehicle_row, self.horizontal_fraction_before_all_bars)

    def drop_vehicle_row_after_all_bars(self, vehicle_row: Locator) -> None:
        self.receive_dragged_element(vehicle_row, self.horizontal_fraction_after_all_bars)

    def drag_bar_before_all_bars_of(self, vehicle_id: str, target_chart: Self) -> None:
        target_chart.receive_dragged_element(self._grab_handle_of_bar(vehicle_id), target_chart.horizontal_fraction_before_all_bars)

    def drag_bar_after_all_bars_of(self, vehicle_id: str, target_chart: Self) -> None:
        target_chart.receive_dragged_element(self._grab_handle_of_bar(vehicle_id), target_chart.horizontal_fraction_after_all_bars)

    def receive_dragged_element(self, dragged_element: Locator, horizontal_fraction: float) -> None:
        self.container.scroll_into_view_if_needed()
        container_box = self.container.bounding_box()
        drop_position = {"x": container_box["width"] * horizontal_fraction, "y": container_box["height"] / 2}
        dragged_element.drag_to(self.container, target_position=drop_position)

    def _grab_handle_of_bar(self, vehicle_id: str) -> Locator:
        return self.bar_of_vehicle(vehicle_id).locator("rect")


class Aut1VehiclesPage(Aut1BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/vehicles_page.html")
        self.accessible_brands_notice = page.get_by_test_id("accessible-brands-notice")
        self.accessible_brands_notice_prefix = "Brands you can access:"
        self.vehicle_table = VehicleTable(page)
        self.add_vehicle_section = page.get_by_test_id("add-vehicle-section")
        self.horsepower_chart = VehicleBarChart(page, "horsepower", "data-power-hp")
        self.price_chart = VehicleBarChart(page, "price", "data-price-eur")

    def wait_until_vehicles_are_listed(self) -> Self:
        expect(self.vehicle_table.rows.first).to_be_visible()
        return self

    def read_accessible_brand_names(self) -> list[str]:
        expect(self.accessible_brands_notice).to_contain_text(self.accessible_brands_notice_prefix)
        notice_text = self.accessible_brands_notice.text_content().removeprefix(self.accessible_brands_notice_prefix)
        return [brand_name.strip() for brand_name in notice_text.split(",")]


class Aut1Application:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.login_page = Aut1LoginPage(page)
        self.home_page = Aut1HomePage(page)
        self.vehicles_page = Aut1VehiclesPage(page)
        self.home_page_url_pattern = re.compile(r"/home_page\.html$")

    def log_in_as(self, username: str, password: str) -> Aut1HomePage:
        self.login_page.open().log_in(username, password)
        expect(self.page).to_have_url(self.home_page_url_pattern)
        return self.home_page

    def open_vehicles_page_as(self, username: str, password: str) -> Aut1VehiclesPage:
        self.log_in_as(username, password)
        return self.vehicles_page.open().wait_until_vehicles_are_listed()
