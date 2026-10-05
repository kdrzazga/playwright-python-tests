from dash import Input, Output, State, ctx, html, no_update

from dealership_analytics.layout import describe_data_source_status, with_test_id


class DashboardCallbacks:
    def __init__(self, app, repository, figure_factory, snapshot_provider):
        self.app = app
        self.repository = repository
        self.figure_factory = figure_factory
        self.snapshot_provider = snapshot_provider

    def register_all(self):
        self._register_live_data_refresh_callback()
        self._register_overview_callbacks()
        self._register_stock_callbacks()
        self._register_loan_callbacks()
        self._register_factory_callbacks()

    def _register_live_data_refresh_callback(self):
        @self.app.callback(
            Output("data-version", "data"),
            Output("data-source-status", "children"),
            Input("data-refresh-interval", "n_intervals"),
            Input("refresh-data-button", "n_clicks"),
            State("data-version", "data"),
            prevent_initial_call=True,
        )
        def refresh_live_data(refresh_tick_count, refresh_click_count, current_data_version):
            snapshot = self.snapshot_provider.refresh()
            status_text = describe_data_source_status(self.snapshot_provider, snapshot)
            if snapshot is None or snapshot.fingerprint() == current_data_version:
                return no_update, status_text
            return snapshot.fingerprint(), status_text

    def _register_overview_callbacks(self):
        as_of_date_text = self.repository.as_of_date.isoformat()

        @self.app.callback(
            Output("overview-key-figures", "children"),
            Output("sales-and-rentals-over-time-graph", "figure"),
            Output("revenue-by-brand-graph", "figure"),
            Input("overview-brand-checklist", "value"),
            Input("overview-date-range", "start_date"),
            Input("overview-date-range", "end_date"),
            Input("data-version", "data"),
        )
        def update_overview(selected_brand_names, start_date, end_date, data_version):
            first_agreement_date, _ = self.repository.find_first_and_last_agreement_dates()
            first_date = (start_date or first_agreement_date)[:10]
            last_date = (end_date or as_of_date_text)[:10]
            key_figures = self.repository.calculate_key_figures(selected_brand_names, first_date, last_date)
            return (
                self._build_key_figure_cards(key_figures),
                self.figure_factory.build_sales_and_rentals_over_time_figure(
                    self.repository.summarize_monthly_sales(selected_brand_names, first_date, last_date),
                    self.repository.summarize_monthly_rental_starts(selected_brand_names, first_date, last_date),
                ),
                self.figure_factory.build_revenue_by_brand_figure(
                    self.repository.summarize_sales_revenue_by_brand(selected_brand_names, first_date, last_date)
                ),
            )

        @self.app.callback(
            Output("overview-brand-checklist", "value"),
            Input("revenue-by-brand-graph", "clickData"),
            Input("overview-reset-brands-button", "n_clicks"),
            prevent_initial_call=True,
        )
        def focus_on_clicked_brand_or_reset(revenue_bar_click, reset_click_count):
            if ctx.triggered_id == "revenue-by-brand-graph" and revenue_bar_click:
                return [revenue_bar_click["points"][0]["x"]]
            return self.repository.list_brand_names_with_vehicles()

    def _register_stock_callbacks(self):
        @self.app.callback(
            Output("stock-table", "data"),
            Output("stock-status-graph", "figure"),
            Output("stock-vehicle-count", "children"),
            Input("stock-brand-dropdown", "value"),
            Input("stock-engine-dropdown", "value"),
            Input("stock-status-checklist", "value"),
            Input("data-version", "data"),
        )
        def update_stock(selected_brand_names, selected_engine_types, selected_statuses, data_version):
            stock_rows = self.repository.list_stock(
                selected_brand_names or [], selected_statuses or [], selected_engine_types or None
            )
            return (
                stock_rows,
                self.figure_factory.build_stock_status_figure(stock_rows),
                f"{len(stock_rows)} vehicles match the filters",
            )

    def _register_loan_callbacks(self):
        @self.app.callback(
            Output("loans-table", "data"),
            Output("loan-principal-by-lender-graph", "figure"),
            Input("loan-status-checklist", "value"),
            Input("data-version", "data"),
        )
        def update_loans(selected_loan_statuses, data_version):
            loans = self.repository.list_loans(selected_loan_statuses or [])
            return loans, self.figure_factory.build_loan_principal_by_lender_figure(loans)

    def _register_factory_callbacks(self):
        current_year = self.repository.as_of_date.year

        @self.app.callback(
            Output("factory-map-graph", "figure"),
            Output("factories-operating-per-year-graph", "figure"),
            Output("factory-count", "children"),
            Input("factory-year-slider", "value"),
            Input("factory-state-checklist", "value"),
            Input("factory-country-dropdown", "value"),
            Input("data-version", "data"),
        )
        def update_factories(selected_year, selected_factory_states, selected_countries, data_version):
            earliest_opening_year = self.repository.find_earliest_factory_opening_year()
            factory_states = selected_factory_states or []
            operating_factories = self.repository.list_factories_operating_in_year(
                selected_year, factory_states, selected_countries or []
            )
            return (
                self.figure_factory.build_factory_map_figure(operating_factories, selected_year),
                self.figure_factory.build_factories_operating_per_year_figure(
                    self.repository.count_factories_operating_per_year(
                        factory_states, selected_countries or [], earliest_opening_year, current_year
                    ),
                    selected_year,
                ),
                f"{len(operating_factories)} factories operating in {selected_year}",
            )

        @self.app.callback(
            Output("factory-detail-panel", "children"),
            Input("factory-map-graph", "clickData"),
            prevent_initial_call=True,
        )
        def show_clicked_factory_details(factory_map_click):
            factory = self.repository.find_factory_by_id(factory_map_click["points"][0]["customdata"])
            if factory is None:
                return "Click a factory on the map to see its details."
            return self._build_factory_details(factory)

    @staticmethod
    def _build_key_figure_cards(key_figures):
        key_figure_definitions = (
            ("vehicles_sold", "Vehicles sold", "{:,}"),
            ("sales_revenue_eur", "Sales revenue", "{:,} EUR"),
            ("vehicles_rented", "Vehicles rented", "{:,}"),
            ("vehicles_available", "Available now", "{:,}"),
            ("active_loan_principal_eur", "Active loan principal (all brands)", "{:,} EUR"),
        )
        return [
            html.Div(
                className="key-figure-card",
                **with_test_id(f"key-figure-{key_figure_name}"),
                children=[
                    html.Span(caption, className="key-figure-caption"),
                    html.Strong(value_format.format(key_figures[key_figure_name]), className="key-figure-value"),
                ],
            )
            for key_figure_name, caption, value_format in key_figure_definitions
        ]

    @staticmethod
    def _build_factory_details(factory):
        detail_rows = (
            ("Manufacturer", factory["manufacturer"]),
            ("Location", f"{factory['city']}, {factory['country']}"),
            ("Opened", str(factory["opened_year"])),
            ("Closed", str(factory["closed_year"]) if factory["closed_year"] else "still active"),
        )
        return [
            html.H3(factory["name"], **with_test_id("factory-detail-name")),
            html.Dl(
                children=[
                    element
                    for label, value in detail_rows
                    for element in (html.Dt(label), html.Dd(value, **with_test_id(f"factory-detail-{label.lower()}")))
                ]
            ),
        ]
