import re
from dataclasses import dataclass
from typing import Self

from playwright.sync_api import Locator, Page, expect


@dataclass(frozen=True)
class VehicleRow:
    cells_by_column_name: dict[str, str]

    @property
    def vehicle_id(self) -> str:
        return self.cell("id")

    def cell(self, column_name: str) -> str:
        return self.cells_by_column_name[column_name]


@dataclass(frozen=True)
class DisplayedBar:
    vehicle_id_label: str
    value_label: str


@dataclass(frozen=True)
class ScreenPoint:
    x: float
    y: float


class MouseDragger:
    def __init__(self, page: Page, intermediate_move_steps: int) -> None:
        self.page = page
        self.intermediate_move_steps = intermediate_move_steps

    def drag(self, start_point: ScreenPoint, end_point: ScreenPoint) -> None:
        self.page.mouse.move(start_point.x, start_point.y)
        self.page.mouse.down()
        self.page.mouse.move(end_point.x, end_point.y, steps=self.intermediate_move_steps)
        self.page.mouse.up()


class ElementGeometry:
    def center_of(self, element: Locator) -> ScreenPoint:
        element_box = element.bounding_box()
        return ScreenPoint(element_box["x"] + element_box["width"] / 2, element_box["y"] + element_box["height"] / 2)

    def point_at_horizontal_fraction_of(self, element: Locator, horizontal_fraction: float) -> ScreenPoint:
        element_box = element.bounding_box()
        return ScreenPoint(element_box["x"] + element_box["width"] * horizontal_fraction, element_box["y"] + element_box["height"] / 2)

    def point_just_above(self, element: Locator, vertical_offset: float) -> ScreenPoint:
        element_box = element.bounding_box()
        return ScreenPoint(element_box["x"] + element_box["width"] / 2, element_box["y"] - vertical_offset)

    def left_edge_of(self, element: Locator) -> float:
        return element.bounding_box()["x"]


class Aut1BasePage:
    def __init__(self, page: Page, path: str) -> None:
        self.page = page
        self.path = path


class Aut1LoginPage(Aut1BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/login_page.html")
        self.username_input = page.get_by_test_id("username-input")
        self.password_input = page.get_by_test_id("password-input")
        self.login_button = page.get_by_test_id("login-button")
        self.error_message = page.get_by_test_id("login-error-message")

    def open(self) -> Self:
        self.page.goto(self.path)
        return self

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

    def row(self, row_index: int) -> Locator:
        return self.rows.nth(row_index)

    def read_row(self, row_index: int) -> VehicleRow:
        return self._read_row_element(self.row(row_index))

    def read_all_rows(self) -> list[VehicleRow]:
        return [self._read_row_element(row_element) for row_element in self.rows.all()]

    def _read_row_element(self, row_element: Locator) -> VehicleRow:
        column_names = [header_text.strip().lower() for header_text in self.header_cells.all_inner_texts()]
        cell_texts = [cell_text.strip() for cell_text in row_element.locator("td").all_inner_texts()]
        return VehicleRow(cells_by_column_name=dict(zip(column_names, cell_texts)))


class VehicleBarChart:
    def __init__(self, page: Page, test_id_prefix: str, mouse_dragger: MouseDragger, element_geometry: ElementGeometry) -> None:
        self.page = page
        self.test_id_prefix = test_id_prefix
        self.mouse_dragger = mouse_dragger
        self.element_geometry = element_geometry
        self.container = page.get_by_test_id(f"{test_id_prefix}-bar-chart")
        self.bar_vehicle_id_labels = self.container.locator(f"[data-testid^='{test_id_prefix}-bar-label-']")
        self.bar_value_labels = self.container.locator(f"[data-testid^='{test_id_prefix}-bar-value-']")
        self.empty_chart_hint = page.get_by_test_id(f"{test_id_prefix}-chart-empty-hint")
        self.x_axis_title = page.get_by_test_id(f"{test_id_prefix}-chart-x-axis-title")
        self.y_axis_title = page.get_by_test_id(f"{test_id_prefix}-chart-y-axis-title")
        self.horizontal_fraction_before_all_bars = 0.03
        self.horizontal_fraction_after_all_bars = 0.97
        self.grab_distance_above_vehicle_id_label = 15

    def read_bars_left_to_right(self) -> list[DisplayedBar]:
        vehicle_id_labels = self._sort_left_to_right(self.bar_vehicle_id_labels.all())
        value_labels = self._sort_left_to_right(self.bar_value_labels.all())
        return [
            DisplayedBar(vehicle_id_label=vehicle_id_label.text_content().strip(), value_label=value_label.text_content().strip())
            for vehicle_id_label, value_label in zip(vehicle_id_labels, value_labels)
        ]

    def drop_vehicle_row_before_all_bars(self, vehicle_row: Locator) -> None:
        self._drag_onto_this_chart(self.element_geometry.center_of(vehicle_row), self.horizontal_fraction_before_all_bars)

    def drop_vehicle_row_after_all_bars(self, vehicle_row: Locator) -> None:
        self._drag_onto_this_chart(self.element_geometry.center_of(vehicle_row), self.horizontal_fraction_after_all_bars)

    def drag_bar_before_all_bars_of(self, vehicle_id_label: str, target_chart: Self) -> None:
        target_chart._drag_onto_this_chart(self._grab_point_of_bar(vehicle_id_label), target_chart.horizontal_fraction_before_all_bars)

    def drag_bar_after_all_bars_of(self, vehicle_id_label: str, target_chart: Self) -> None:
        target_chart._drag_onto_this_chart(self._grab_point_of_bar(vehicle_id_label), target_chart.horizontal_fraction_after_all_bars)

    def _drag_onto_this_chart(self, start_point: ScreenPoint, horizontal_fraction: float) -> None:
        drop_point = self.element_geometry.point_at_horizontal_fraction_of(self.container, horizontal_fraction)
        self.mouse_dragger.drag(start_point, drop_point)

    def _grab_point_of_bar(self, vehicle_id_label: str) -> ScreenPoint:
        visible_vehicle_id_label = self.bar_vehicle_id_labels.filter(has_text=re.compile(rf"^{re.escape(vehicle_id_label)}$"))
        return self.element_geometry.point_just_above(visible_vehicle_id_label, self.grab_distance_above_vehicle_id_label)

    def _sort_left_to_right(self, elements: list[Locator]) -> list[Locator]:
        return sorted(elements, key=self.element_geometry.left_edge_of)


class Aut1VehiclesPage(Aut1BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/vehicles_page.html")
        mouse_dragger = MouseDragger(page, intermediate_move_steps=10)
        element_geometry = ElementGeometry()
        self.accessible_brands_notice = page.get_by_test_id("accessible-brands-notice")
        self.accessible_brands_notice_prefix = "Brands you can access:"
        self.vehicle_table = VehicleTable(page)
        self.horsepower_chart = VehicleBarChart(page, "horsepower", mouse_dragger, element_geometry)
        self.price_chart = VehicleBarChart(page, "price", mouse_dragger, element_geometry)

    def wait_until_vehicles_are_listed(self) -> Self:
        expect(self.vehicle_table.rows.first).to_be_visible()
        return self

    def read_accessible_brand_names(self) -> list[str]:
        expect(self.accessible_brands_notice).to_contain_text(self.accessible_brands_notice_prefix)
        notice_text = self.accessible_brands_notice.inner_text().strip().removeprefix(self.accessible_brands_notice_prefix)
        return [brand_name.strip() for brand_name in notice_text.split(",")]


class Aut1UserInterface:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.login_page = Aut1LoginPage(page)
        self.home_page = Aut1HomePage(page)
        self.vehicles_page = Aut1VehiclesPage(page)
        self.home_page_url_pattern = re.compile(r"/home_page\.html$")
        self.vehicles_page_url_pattern = re.compile(r"/vehicles_page\.html$")

    def log_in_as(self, username: str, password: str) -> Aut1HomePage:
        self.login_page.open().log_in(username, password)
        expect(self.page).to_have_url(self.home_page_url_pattern)
        return self.home_page

    def go_to_vehicles_page_as(self, username: str, password: str) -> Aut1VehiclesPage:
        self.log_in_as(username, password).vehicles_button.click()
        expect(self.page).to_have_url(self.vehicles_page_url_pattern)
        return self.vehicles_page.wait_until_vehicles_are_listed()
