import pytest
from playwright.sync_api import expect

from pom import Aut1VehiclesPage, DisplayedBar, VehicleBarChart
from pom.aut1 import VehicleRow
from tests.compact_number_format import CompactEnglishNumberFormat
from tests.eventual_assertion import EventualAssertion


pytestmark = [pytest.mark.aut1, pytest.mark.drag_and_drop]


class TestVehicleComparisonCharts:
    def _expect_bars_left_to_right(self, eventually: EventualAssertion, chart: VehicleBarChart, expected_bars: list[DisplayedBar]) -> None:
        eventually.assert_equal(chart.read_bars_left_to_right, expected_bars)

    def _horsepower_bar_of(self, vehicle_row: VehicleRow) -> DisplayedBar:
        return DisplayedBar(vehicle_id_label=vehicle_row.vehicle_id, value_label=vehicle_row.cell("power_hp"))

    def _price_bar_of(self, vehicle_row: VehicleRow, compact_number_format: CompactEnglishNumberFormat) -> DisplayedBar:
        return DisplayedBar(vehicle_id_label=vehicle_row.vehicle_id, value_label=compact_number_format.format(vehicle_row.cell("price_eur")))

    @pytest.mark.smoke
    @pytest.mark.dnd
    def test_dropped_vehicle_rows_are_inserted_at_drop_position_without_duplicates(
        self, dealer_vehicles_page: Aut1VehiclesPage, eventually: EventualAssertion
    ) -> None:
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

        self._expect_bars_left_to_right(
            eventually, horsepower_chart, [self._horsepower_bar_of(second_vehicle), self._horsepower_bar_of(first_vehicle)]
        )
        expect(horsepower_chart.empty_chart_hint).to_have_count(0)

    @pytest.mark.dnd
    def test_bar_moves_between_charts_and_reorders_within_chart(
        self, dealer_vehicles_page: Aut1VehiclesPage, eventually: EventualAssertion, compact_number_format: CompactEnglishNumberFormat
    ) -> None:
        vehicle_table = dealer_vehicles_page.vehicle_table
        horsepower_chart = dealer_vehicles_page.horsepower_chart
        price_chart = dealer_vehicles_page.price_chart
        first_vehicle = vehicle_table.read_row(0)
        second_vehicle = vehicle_table.read_row(1)
        horsepower_chart.drop_vehicle_row_after_all_bars(vehicle_table.row(0))
        horsepower_chart.drop_vehicle_row_after_all_bars(vehicle_table.row(1))
        self._expect_bars_left_to_right(
            eventually, horsepower_chart, [self._horsepower_bar_of(first_vehicle), self._horsepower_bar_of(second_vehicle)]
        )

        horsepower_chart.drag_bar_after_all_bars_of(first_vehicle.vehicle_id, price_chart)

        self._expect_bars_left_to_right(eventually, horsepower_chart, [self._horsepower_bar_of(second_vehicle)])
        self._expect_bars_left_to_right(eventually, price_chart, [self._price_bar_of(first_vehicle, compact_number_format)])

        price_chart.drag_bar_after_all_bars_of(first_vehicle.vehicle_id, horsepower_chart)

        self._expect_bars_left_to_right(eventually, price_chart, [])
        expect(price_chart.empty_chart_hint).to_be_visible()
        self._expect_bars_left_to_right(
            eventually, horsepower_chart, [self._horsepower_bar_of(second_vehicle), self._horsepower_bar_of(first_vehicle)]
        )

        horsepower_chart.drag_bar_before_all_bars_of(first_vehicle.vehicle_id, horsepower_chart)

        self._expect_bars_left_to_right(
            eventually, horsepower_chart, [self._horsepower_bar_of(first_vehicle), self._horsepower_bar_of(second_vehicle)]
        )
