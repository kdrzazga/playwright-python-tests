from collections import Counter, defaultdict

import plotly.graph_objects as graph_objects


class DashboardFigureFactory:
    def __init__(
        self,
        primary_color="#1f6feb",
        secondary_color="#f28e2b",
        active_factory_color="#2e7d32",
        closed_factory_color="#c62828",
        status_colors=None,
        duplicate_location_longitude_offset=0.6,
    ):
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.active_factory_color = active_factory_color
        self.closed_factory_color = closed_factory_color
        self.status_colors = status_colors or {"available": "#2e7d32", "rented": "#f28e2b", "sold": "#9e9e9e"}
        self.duplicate_location_longitude_offset = duplicate_location_longitude_offset

    def build_sales_and_rentals_over_time_figure(self, monthly_sales, monthly_rental_starts):
        figure = graph_objects.Figure()
        figure.add_trace(
            graph_objects.Bar(
                name="Vehicles sold",
                x=[month["month"] for month in monthly_sales],
                y=[month["vehicles_sold"] for month in monthly_sales],
                marker_color=self.primary_color,
            )
        )
        figure.add_trace(
            graph_objects.Scatter(
                name="Vehicles rented",
                mode="lines+markers",
                x=[month["month"] for month in monthly_rental_starts],
                y=[month["vehicles_rented"] for month in monthly_rental_starts],
                line_color=self.secondary_color,
            )
        )
        figure.update_layout(title="Vehicles sold and rented per month", xaxis_title="Month", yaxis_title="Vehicles")
        return self._apply_common_layout(figure)

    def build_revenue_by_brand_figure(self, revenue_by_brand):
        figure = graph_objects.Figure(
            graph_objects.Bar(
                x=[brand_revenue["brand"] for brand_revenue in revenue_by_brand],
                y=[round(brand_revenue["revenue_eur"]) for brand_revenue in revenue_by_brand],
                customdata=[brand_revenue["vehicles_sold"] for brand_revenue in revenue_by_brand],
                hovertemplate="%{x}<br>%{y:,.0f} EUR<br>%{customdata} vehicles sold<extra></extra>",
                marker_color=self.primary_color,
            )
        )
        figure.update_layout(title="Sales revenue by brand (click a bar to focus)", yaxis_title="Revenue (EUR)")
        return self._apply_common_layout(figure)

    def build_stock_status_figure(self, stock_rows):
        status_counts = Counter(stock_row["status"] for stock_row in stock_rows)
        statuses = sorted(status_counts)
        figure = graph_objects.Figure(
            graph_objects.Pie(
                labels=statuses,
                values=[status_counts[status] for status in statuses],
                hole=0.5,
                marker_colors=[self.status_colors.get(status) for status in statuses],
                sort=False,
            )
        )
        figure.update_layout(title="Vehicles by status")
        return self._apply_common_layout(figure)

    def build_loan_principal_by_lender_figure(self, loans):
        principal_by_lender = defaultdict(int)
        lender_type_by_lender = {}
        for loan in loans:
            principal_by_lender[loan["lender"]] += loan["principal_eur"]
            lender_type_by_lender[loan["lender"]] = loan["lender_type"]
        lenders = sorted(principal_by_lender, key=principal_by_lender.get, reverse=True)
        figure = graph_objects.Figure(
            graph_objects.Bar(
                x=lenders,
                y=[principal_by_lender[lender] for lender in lenders],
                customdata=[lender_type_by_lender[lender] for lender in lenders],
                hovertemplate="%{x} (%{customdata})<br>%{y:,.0f} EUR<extra></extra>",
                marker_color=[
                    self.primary_color if lender_type_by_lender[lender] == "bank" else self.secondary_color
                    for lender in lenders
                ],
            )
        )
        figure.update_layout(title="Financed principal by lender (blue: bank, orange: leasing)", yaxis_title="Principal (EUR)")
        return self._apply_common_layout(figure)

    def build_factory_map_figure(self, factories, selected_year):
        figure = graph_objects.Figure()
        positioned_factories = self._spread_factories_sharing_a_location(factories)
        for still_active, trace_name, trace_color in (
            (True, "Still active", self.active_factory_color),
            (False, "Closed since", self.closed_factory_color),
        ):
            trace_factories = [factory for factory in positioned_factories if bool(factory["active"]) is still_active]
            figure.add_trace(
                graph_objects.Scattergeo(
                    name=trace_name,
                    lat=[factory["display_latitude"] for factory in trace_factories],
                    lon=[factory["display_longitude"] for factory in trace_factories],
                    customdata=[factory["id"] for factory in trace_factories],
                    text=[self._describe_factory_for_hover(factory) for factory in trace_factories],
                    hovertemplate="%{text}<extra></extra>",
                    mode="markers",
                    marker={"size": 9, "color": trace_color, "line": {"width": 1, "color": "white"}},
                )
            )
        figure.update_layout(
            title=f"Car factories operating in {selected_year}",
            geo={"projection_type": "natural earth", "showcountries": True, "showland": True, "landcolor": "#f3f5f8"},
            height=520,
        )
        return self._apply_common_layout(figure)

    def build_factories_operating_per_year_figure(self, operating_counts_by_year, selected_year):
        years = sorted(operating_counts_by_year)
        figure = graph_objects.Figure(
            graph_objects.Scatter(
                x=years,
                y=[operating_counts_by_year[year] for year in years],
                mode="lines",
                line_color=self.primary_color,
                hovertemplate="%{x}: %{y} factories<extra></extra>",
            )
        )
        figure.add_vline(x=selected_year, line_dash="dash", line_color=self.secondary_color)
        figure.update_layout(title="Factories operating per year", xaxis_title="Year", yaxis_title="Factories")
        return self._apply_common_layout(figure)

    def _spread_factories_sharing_a_location(self, factories):
        factories_seen_at_location = Counter()
        positioned_factories = []
        for factory in factories:
            location = (factory["latitude"], factory["longitude"])
            earlier_factories_at_location = factories_seen_at_location[location]
            factories_seen_at_location[location] += 1
            positioned_factories.append(
                {
                    **factory,
                    "display_latitude": factory["latitude"],
                    "display_longitude": factory["longitude"]
                    + earlier_factories_at_location * self.duplicate_location_longitude_offset,
                }
            )
        return positioned_factories

    @staticmethod
    def _describe_factory_for_hover(factory):
        operating_years = f"{factory['opened_year']}-{factory['closed_year'] or 'today'}"
        return f"<b>{factory['name']}</b><br>{factory['manufacturer']}<br>{factory['city']}, {factory['country']}<br>{operating_years}"

    @staticmethod
    def _apply_common_layout(figure):
        figure.update_layout(
            margin={"l": 40, "r": 20, "t": 50, "b": 40},
            paper_bgcolor="white",
            plot_bgcolor="white",
            legend={"orientation": "h", "y": -0.15},
        )
        return figure
