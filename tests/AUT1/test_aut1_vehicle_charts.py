import pytest
from playwright.sync_api import expect

from pom import Aut1VehiclesPage
from pom.aut1 import VehicleBarChart


pytestmark = [pytest.mark.aut1, pytest.mark.drag_and_drop]


class TestVehicleComparisonCharts:
    def _expect_bars_in_display_order(self, chart: VehicleBarChart, expected_vehicle_ids: list[str]) -> None:
        expect(chart.bars).to_have_count(len(expected_vehicle_ids))
        for display_position, expected_vehicle_id in enumerate(expected_vehicle_ids):
            expect(chart.bar_at_display_position(display_position)).to_have_attribute("data-vehicle-id", expected_vehicle_id)

    @pytest.mark.smoke
    @pytest.mark.dnd
    def test_dropped_vehicle_rows_are_inserted_at_drop_position_without_duplicates(self, dealer_vehicles_page: Aut1VehiclesPage) -> None:
        vehicle_table = dealer_vehicles_page.vehicle_table
        horsepower_chart = dealer_vehicles_page.horsepower_chart
        first_vehicle = vehicle_table.read_row(0)
        second_vehicle = vehicle_table.read_row(1)
        expect(horsepower_chart.empty_chart_hint).to_be_visible()
        expect(horsepower_chart.x_axis_title).to_have_text("ID")
        expect(horsepower_chart.y_axis_title).to_have_text("HP")

        horsepower_chart.drop_vehicle_row_after_all_bars(vehicle_table.row(0))
        horsepower_chart.drop_vehicle_row_before_all_bars(vehicle_table.row(1))
        horsepower_chart.drop_vehicle_row_before_all_bars(vehicle_table.row(0))

        self._expect_bars_in_display_order(horsepower_chart, [second_vehicle.vehicle_id, first_vehicle.vehicle_id])
        expect(horsepower_chart.empty_chart_hint).to_have_count(0)
        for charted_vehicle in (first_vehicle, second_vehicle):
            expect(horsepower_chart.bar_of_vehicle(charted_vehicle.vehicle_id)).to_have_attribute(
                horsepower_chart.charted_value_attribute_name, charted_vehicle.cell("power_hp")
            )

    @pytest.mark.dnd
    def test_bar_moves_between_charts_and_reorders_within_chart(self, dealer_vehicles_page: Aut1VehiclesPage) -> None:
        vehicle_table = dealer_vehicles_page.vehicle_table
        horsepower_chart = dealer_vehicles_page.horsepower_chart
        price_chart = dealer_vehicles_page.price_chart
        first_vehicle = vehicle_table.read_row(0)
        second_vehicle = vehicle_table.read_row(1)
        horsepower_chart.drop_vehicle_row_after_all_bars(vehicle_table.row(0))
        horsepower_chart.drop_vehicle_row_after_all_bars(vehicle_table.row(1))
        self._expect_bars_in_display_order(horsepower_chart, [first_vehicle.vehicle_id, second_vehicle.vehicle_id])

        horsepower_chart.drag_bar_after_all_bars_of(first_vehicle.vehicle_id, price_chart)

        self._expect_bars_in_display_order(horsepower_chart, [second_vehicle.vehicle_id])
        expect(price_chart.bar_of_vehicle(first_vehicle.vehicle_id)).to_have_attribute(
            price_chart.charted_value_attribute_name, first_vehicle.cell("price_eur")
        )

        price_chart.drag_bar_after_all_bars_of(first_vehicle.vehicle_id, horsepower_chart)

        self._expect_bars_in_display_order(price_chart, [])
        expect(price_chart.empty_chart_hint).to_be_visible()
        self._expect_bars_in_display_order(horsepower_chart, [second_vehicle.vehicle_id, first_vehicle.vehicle_id])

        horsepower_chart.drag_bar_before_all_bars_of(first_vehicle.vehicle_id, horsepower_chart)

        self._expect_bars_in_display_order(horsepower_chart, [first_vehicle.vehicle_id, second_vehicle.vehicle_id])
