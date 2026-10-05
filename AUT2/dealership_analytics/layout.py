from dash import dash_table, dcc, html

from dealership_analytics.analytics_repository import VehicleStatus
from dealership_analytics.aut1_api_client import Aut1UnavailableError


def with_test_id(test_id):
    return {"data-testid": test_id}


def describe_data_source_status(snapshot_provider, snapshot):
    if snapshot is None:
        return f"AUT1 at {snapshot_provider.source_description} is not reachable: {snapshot_provider.latest_error}"
    status_text = f"Live data from AUT1 at {snapshot_provider.source_description}, refreshed {snapshot.fetched_at:%H:%M:%S}"
    if snapshot_provider.latest_error:
        status_text += f". Last refresh failed ({snapshot_provider.latest_error}); showing the previous data"
    return status_text


class DashboardLayoutBuilder:
    def __init__(
        self,
        repository,
        snapshot_provider,
        refresh_interval_seconds,
        records_per_table_page=15,
        factory_slider_mark_interval_years=20,
    ):
        self.repository = repository
        self.snapshot_provider = snapshot_provider
        self.refresh_interval_seconds = refresh_interval_seconds
        self.records_per_table_page = records_per_table_page
        self.factory_slider_mark_interval_years = factory_slider_mark_interval_years

    def build_layout(self):
        try:
            snapshot = self.snapshot_provider.current_snapshot()
        except Aut1UnavailableError as error:
            return self._build_aut1_unavailable_layout(error)
        return html.Div(
            className="dashboard",
            children=[
                html.Header(
                    className="dashboard-header",
                    children=[
                        html.H1("Dealership Analytics", **with_test_id("dashboard-title")),
                        html.P(
                            f"Data as of {self.repository.as_of_date.isoformat()}",
                            className="muted-text",
                            **with_test_id("as-of-date"),
                        ),
                        html.Div(
                            className="data-source-bar",
                            children=[
                                html.Span(
                                    describe_data_source_status(self.snapshot_provider, snapshot),
                                    id="data-source-status",
                                    **with_test_id("data-source-status"),
                                ),
                                html.Button("Refresh now", id="refresh-data-button", className="secondary-button"),
                            ],
                        ),
                        dcc.Interval(id="data-refresh-interval", interval=self.refresh_interval_seconds * 1000),
                        dcc.Store(id="data-version", data=snapshot.fingerprint()),
                    ],
                ),
                dcc.Tabs(
                    id="dashboard-tabs",
                    value="overview-tab",
                    className="dashboard-tabs",
                    children=[
                        dcc.Tab(label="Overview", value="overview-tab", id="overview-tab", children=self._build_overview_tab()),
                        dcc.Tab(label="Stock", value="stock-tab", id="stock-tab", children=self._build_stock_tab()),
                        dcc.Tab(label="Loans", value="loans-tab", id="loans-tab", children=self._build_loans_tab()),
                        dcc.Tab(label="Factories", value="factories-tab", id="factories-tab", children=self._build_factories_tab()),
                    ],
                ),
            ],
        )

    def _build_overview_tab(self):
        brand_names = self.repository.list_brand_names_with_vehicles()
        first_agreement_date, _ = self.repository.find_first_and_last_agreement_dates()
        return html.Div(
            className="tab-content",
            **with_test_id("overview-tab-content"),
            children=[
                html.Div(
                    className="filter-row",
                    children=[
                        self._labelled("Brands", dcc.Checklist(
                            id="overview-brand-checklist",
                            options=brand_names,
                            value=brand_names,
                            inline=True,
                        )),
                        html.Button("All brands", id="overview-reset-brands-button", className="secondary-button"),
                        self._labelled("Agreement dates", dcc.DatePickerRange(
                            id="overview-date-range",
                            start_date=first_agreement_date,
                            end_date=self.repository.as_of_date.isoformat(),
                            min_date_allowed=first_agreement_date,
                            max_date_allowed=self.repository.as_of_date.isoformat(),
                            display_format="YYYY-MM-DD",
                        )),
                    ],
                ),
                html.Div(id="overview-key-figures", className="key-figures", **with_test_id("overview-key-figures")),
                dcc.Loading(
                    type="circle",
                    children=[
                        dcc.Graph(id="sales-and-rentals-over-time-graph"),
                        dcc.Graph(id="revenue-by-brand-graph"),
                    ],
                ),
            ],
        )

    def _build_stock_tab(self):
        brand_names = self.repository.list_brand_names_with_vehicles()
        stock_columns = (
            ("id", "ID", "numeric"),
            ("brand", "Brand", "text"),
            ("model", "Model", "text"),
            ("manufacture_year", "Year", "numeric"),
            ("engine", "Engine", "text"),
            ("condition", "Condition", "text"),
            ("mileage_km", "Mileage (km)", "numeric"),
            ("price_eur", "Price (EUR)", "numeric"),
            ("daily_rental_rate_eur", "Daily rate (EUR)", "numeric"),
            ("status", "Status", "text"),
        )
        return html.Div(
            className="tab-content",
            **with_test_id("stock-tab-content"),
            children=[
                html.Div(
                    className="filter-row",
                    children=[
                        self._labelled("Brands", dcc.Dropdown(
                            id="stock-brand-dropdown", options=brand_names, value=brand_names, multi=True,
                        )),
                        self._labelled("Engines", dcc.Dropdown(
                            id="stock-engine-dropdown",
                            options=self.repository.list_engine_types(),
                            value=[],
                            multi=True,
                            placeholder="All engines",
                        )),
                        self._labelled("Status", dcc.Checklist(
                            id="stock-status-checklist",
                            options=[status.value for status in VehicleStatus],
                            value=[status.value for status in VehicleStatus],
                            inline=True,
                        )),
                    ],
                ),
                html.P(id="stock-vehicle-count", className="muted-text", **with_test_id("stock-vehicle-count")),
                html.Div(
                    className="two-column",
                    children=[
                        dcc.Graph(id="stock-status-graph", className="narrow-column"),
                        dash_table.DataTable(
                            id="stock-table",
                            columns=[
                                {"id": column_id, "name": column_name, "type": column_type}
                                for column_id, column_name, column_type in stock_columns
                            ],
                            page_size=self.records_per_table_page,
                            page_action="native",
                            sort_action="native",
                            filter_action="native",
                            style_table={"overflowX": "auto"},
                            style_cell={"padding": "6px 10px", "textAlign": "left", "fontFamily": "inherit"},
                            style_header={"fontWeight": "600", "backgroundColor": "#f3f5f8"},
                            style_data_conditional=[
                                {"if": {"filter_query": f'{{status}} = "{status.value}"', "column_id": "status"},
                                 "color": color, "fontWeight": "600"}
                                for status, color in (
                                    (VehicleStatus.AVAILABLE, "#2e7d32"),
                                    (VehicleStatus.RENTED, "#ef6c00"),
                                    (VehicleStatus.SOLD, "#757575"),
                                )
                            ],
                        ),
                    ],
                ),
            ],
        )

    def _build_loans_tab(self):
        loan_statuses = self.repository.list_loan_statuses()
        loan_columns = (
            ("id", "ID", "numeric"),
            ("lender", "Lender", "text"),
            ("lender_type", "Lender type", "text"),
            ("financed_agreement", "Finances", "text"),
            ("start_date", "Start", "text"),
            ("principal_eur", "Principal (EUR)", "numeric"),
            ("annual_interest_rate_pct", "Rate (%)", "numeric"),
            ("term_months", "Term (months)", "numeric"),
            ("monthly_installment_eur", "Instalment (EUR)", "numeric"),
            ("total_interest_eur", "Total interest (EUR)", "numeric"),
            ("loan_status", "Status", "text"),
        )
        return html.Div(
            className="tab-content",
            **with_test_id("loans-tab-content"),
            children=[
                html.Div(
                    className="filter-row",
                    children=[
                        self._labelled("Loan status", dcc.Checklist(
                            id="loan-status-checklist", options=loan_statuses, value=loan_statuses, inline=True,
                        )),
                    ],
                ),
                dcc.Graph(id="loan-principal-by-lender-graph"),
                dash_table.DataTable(
                    id="loans-table",
                    columns=[
                        {"id": column_id, "name": column_name, "type": column_type}
                        for column_id, column_name, column_type in loan_columns
                    ],
                    page_size=self.records_per_table_page,
                    sort_action="native",
                    style_table={"overflowX": "auto"},
                    style_cell={"padding": "6px 10px", "textAlign": "left", "fontFamily": "inherit"},
                    style_header={"fontWeight": "600", "backgroundColor": "#f3f5f8"},
                ),
            ],
        )

    def _build_factories_tab(self):
        earliest_opening_year = self.repository.find_earliest_factory_opening_year()
        current_year = self.repository.as_of_date.year
        first_marked_year = earliest_opening_year - earliest_opening_year % self.factory_slider_mark_interval_years
        return html.Div(
            className="tab-content",
            **with_test_id("factories-tab-content"),
            children=[
                html.Div(
                    className="filter-row",
                    children=[
                        self._labelled("Factory state today", dcc.Checklist(
                            id="factory-state-checklist",
                            options=[
                                {"label": "Still active", "value": "active"},
                                {"label": "Closed since", "value": "closed"},
                            ],
                            value=["active", "closed"],
                            inline=True,
                        )),
                        self._labelled("Countries", dcc.Dropdown(
                            id="factory-country-dropdown",
                            options=self.repository.list_factory_countries(),
                            value=[],
                            multi=True,
                            placeholder="All countries",
                        )),
                    ],
                ),
                self._labelled("Year", dcc.Slider(
                    id="factory-year-slider",
                    min=earliest_opening_year,
                    max=current_year,
                    step=1,
                    value=current_year,
                    marks={
                        year: str(year)
                        for year in range(first_marked_year, current_year + 1, self.factory_slider_mark_interval_years)
                        if year >= earliest_opening_year
                    },
                    tooltip={"placement": "bottom", "always_visible": True},
                    updatemode="mouseup",
                )),
                html.P(id="factory-count", className="muted-text", **with_test_id("factory-count")),
                html.Div(
                    className="two-column",
                    children=[
                        dcc.Graph(id="factory-map-graph", className="wide-column"),
                        html.Div(
                            id="factory-detail-panel",
                            className="detail-panel narrow-column",
                            **with_test_id("factory-detail-panel"),
                            children="Click a factory on the map to see its details.",
                        ),
                    ],
                ),
                dcc.Graph(id="factories-operating-per-year-graph"),
            ],
        )

    def _build_aut1_unavailable_layout(self, error):
        return html.Div(
            className="dashboard",
            children=[
                html.H1("Dealership Analytics", **with_test_id("dashboard-title")),
                html.Div(
                    className="error-panel",
                    **with_test_id("data-source-error"),
                    children=[
                        html.P(f"No data: {error}"),
                        html.P(f"Start AUT1 at {self.snapshot_provider.source_description} and reload this page."),
                    ],
                ),
            ],
        )

    @staticmethod
    def _labelled(label_text, control):
        return html.Div(className="labelled-control", children=[html.Label(label_text), control])
