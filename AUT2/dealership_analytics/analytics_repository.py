from collections import Counter
from enum import StrEnum


class VehicleStatus(StrEnum):
    AVAILABLE = "available"
    RENTED = "rented"
    SOLD = "sold"


class DealershipAnalyticsRepository:
    def __init__(self, database, as_of_date):
        self.database = database
        self.as_of_date = as_of_date

    def list_brand_names_with_vehicles(self):
        brand_rows = self.database.connection.fetch_all_rows(
            f"SELECT DISTINCT brand FROM {self.database.vehicles.qualified_table_name} ORDER BY brand"
        )
        return [brand_row["brand"] for brand_row in brand_rows]

    def list_engine_types(self):
        engine_rows = self.database.connection.fetch_all_rows(
            f"SELECT DISTINCT engine FROM {self.database.vehicles.qualified_table_name} ORDER BY engine"
        )
        return [engine_row["engine"] for engine_row in engine_rows]

    def find_first_and_last_agreement_dates(self):
        date_bounds_row = self.database.connection.fetch_single_row(
            f"SELECT MIN(agreement_date) AS first_date, MAX(agreement_date) AS last_date FROM ("
            f"SELECT sale_date AS agreement_date FROM {self.database.sale_agreements.qualified_table_name} "
            f"UNION ALL SELECT start_date FROM {self.database.rental_agreements.qualified_table_name})"
        )
        return date_bounds_row["first_date"], date_bounds_row["last_date"]

    def summarize_monthly_sales(self, brand_names, first_date, last_date):
        brand_placeholders = self._placeholders_for(brand_names)
        sale_rows = self.database.connection.fetch_all_rows(
            f"SELECT substr(sale_agreement.sale_date, 1, 7) AS month, COUNT(sale_line.id) AS vehicles_sold, "
            f"SUM(sale_line.price_eur * (100 - sale_agreement.discount_pct) / 100.0) AS revenue_eur "
            f"FROM {self.database.sales.qualified_table_name} AS sale_line "
            f"JOIN {self.database.sale_agreements.qualified_table_name} AS sale_agreement "
            f"ON sale_agreement.id = sale_line.sale_agreement_id "
            f"JOIN {self.database.vehicles.qualified_table_name} AS vehicle ON vehicle.id = sale_line.vehicle_id "
            f"WHERE vehicle.brand IN ({brand_placeholders}) AND sale_agreement.sale_date BETWEEN ? AND ? "
            f"GROUP BY month ORDER BY month",
            (*brand_names, first_date, last_date),
        )
        return [dict(sale_row) for sale_row in sale_rows]

    def summarize_monthly_rental_starts(self, brand_names, first_date, last_date):
        brand_placeholders = self._placeholders_for(brand_names)
        rental_rows = self.database.connection.fetch_all_rows(
            f"SELECT substr(rental_agreement.start_date, 1, 7) AS month, COUNT(rental_line.id) AS vehicles_rented "
            f"FROM {self.database.rentals.qualified_table_name} AS rental_line "
            f"JOIN {self.database.rental_agreements.qualified_table_name} AS rental_agreement "
            f"ON rental_agreement.id = rental_line.rental_agreement_id "
            f"JOIN {self.database.vehicles.qualified_table_name} AS vehicle ON vehicle.id = rental_line.vehicle_id "
            f"WHERE vehicle.brand IN ({brand_placeholders}) AND rental_agreement.start_date BETWEEN ? AND ? "
            f"GROUP BY month ORDER BY month",
            (*brand_names, first_date, last_date),
        )
        return [dict(rental_row) for rental_row in rental_rows]

    def summarize_sales_revenue_by_brand(self, brand_names, first_date, last_date):
        brand_placeholders = self._placeholders_for(brand_names)
        revenue_rows = self.database.connection.fetch_all_rows(
            f"SELECT vehicle.brand AS brand, COUNT(sale_line.id) AS vehicles_sold, "
            f"SUM(sale_line.price_eur * (100 - sale_agreement.discount_pct) / 100.0) AS revenue_eur "
            f"FROM {self.database.sales.qualified_table_name} AS sale_line "
            f"JOIN {self.database.sale_agreements.qualified_table_name} AS sale_agreement "
            f"ON sale_agreement.id = sale_line.sale_agreement_id "
            f"JOIN {self.database.vehicles.qualified_table_name} AS vehicle ON vehicle.id = sale_line.vehicle_id "
            f"WHERE vehicle.brand IN ({brand_placeholders}) AND sale_agreement.sale_date BETWEEN ? AND ? "
            f"GROUP BY vehicle.brand ORDER BY revenue_eur DESC",
            (*brand_names, first_date, last_date),
        )
        return [dict(revenue_row) for revenue_row in revenue_rows]

    def calculate_key_figures(self, brand_names, first_date, last_date):
        monthly_sales = self.summarize_monthly_sales(brand_names, first_date, last_date)
        monthly_rental_starts = self.summarize_monthly_rental_starts(brand_names, first_date, last_date)
        status_counts = Counter(
            stock_row["status"] for stock_row in self.list_stock(brand_names, tuple(VehicleStatus), engine_types=None)
        )
        return {
            "vehicles_sold": sum(month["vehicles_sold"] for month in monthly_sales),
            "sales_revenue_eur": round(sum(month["revenue_eur"] for month in monthly_sales)),
            "vehicles_rented": sum(month["vehicles_rented"] for month in monthly_rental_starts),
            "vehicles_available": status_counts[VehicleStatus.AVAILABLE],
            "active_loan_principal_eur": self._sum_active_loan_principal_eur(),
        }

    def list_stock(self, brand_names, statuses, engine_types):
        status_by_vehicle_id = self._determine_status_of_every_vehicle()
        stock_rows = []
        for vehicle in self.database.vehicles.list_records_on_page(1, self._count_vehicles()):
            vehicle_status = status_by_vehicle_id[vehicle.id]
            if vehicle.brand not in brand_names or vehicle_status not in statuses:
                continue
            if engine_types and vehicle.engine.value not in engine_types:
                continue
            stock_rows.append(
                {
                    "id": vehicle.id,
                    "brand": vehicle.brand,
                    "model": vehicle.model,
                    "manufacture_year": vehicle.manufacture_year,
                    "engine": vehicle.engine.value,
                    "condition": vehicle.condition.value,
                    "mileage_km": vehicle.mileage_km,
                    "price_eur": vehicle.price_eur,
                    "daily_rental_rate_eur": vehicle.daily_rental_rate_eur,
                    "status": vehicle_status.value,
                }
            )
        return stock_rows

    def list_loans(self, loan_statuses):
        status_placeholders = self._placeholders_for(loan_statuses)
        loan_rows = self.database.connection.fetch_all_rows(
            f"SELECT loan.id, lender.name AS lender, loan.lender_company_type AS lender_type, "
            f"CASE WHEN loan.sale_agreement_id IS NOT NULL THEN 'sale ' || loan.sale_agreement_id "
            f"ELSE 'rental ' || loan.rental_agreement_id END AS financed_agreement, "
            f"loan.start_date, loan.principal_eur, loan.annual_interest_rate_pct, loan.term_months, "
            f"loan.monthly_installment_eur, "
            f"ROUND(loan.monthly_installment_eur * loan.term_months - loan.principal_eur, 2) AS total_interest_eur, "
            f"loan.loan_status "
            f"FROM {self.database.loans.qualified_table_name} AS loan "
            f"JOIN {self.database.companies.qualified_table_name} AS lender ON lender.id = loan.lender_company_id "
            f"WHERE loan.loan_status IN ({status_placeholders}) ORDER BY loan.id",
            tuple(loan_statuses),
        )
        return [dict(loan_row) for loan_row in loan_rows]

    def list_loan_statuses(self):
        status_rows = self.database.connection.fetch_all_rows(
            f"SELECT DISTINCT loan_status FROM {self.database.loans.qualified_table_name} ORDER BY loan_status"
        )
        return [status_row["loan_status"] for status_row in status_rows]

    def list_factories(self):
        factory_rows = self.database.connection.fetch_all_rows(
            f"SELECT * FROM {self.database.reference_factories.qualified_table_name} ORDER BY id"
        )
        return [dict(factory_row) for factory_row in factory_rows]

    def list_factory_countries(self):
        return sorted({factory["country"] for factory in self.list_factories()})

    def find_factory_by_id(self, factory_id):
        return next((factory for factory in self.list_factories() if factory["id"] == factory_id), None)

    def find_earliest_factory_opening_year(self):
        return min(factory["opened_year"] for factory in self.list_factories())

    def list_factories_operating_in_year(self, year, factory_states, countries):
        return [
            factory
            for factory in self._list_factories_matching(factory_states, countries)
            if self._factory_operated_in_year(factory, year)
        ]

    def count_factories_operating_per_year(self, factory_states, countries, first_year, last_year):
        matching_factories = self._list_factories_matching(factory_states, countries)
        return {
            year: sum(1 for factory in matching_factories if self._factory_operated_in_year(factory, year))
            for year in range(first_year, last_year + 1)
        }

    def _list_factories_matching(self, factory_states, countries):
        return [
            factory
            for factory in self.list_factories()
            if ("active" if factory["active"] else "closed") in factory_states
            and (not countries or factory["country"] in countries)
        ]

    @staticmethod
    def _factory_operated_in_year(factory, year):
        return factory["opened_year"] <= year and (factory["closed_year"] is None or factory["closed_year"] >= year)

    def _determine_status_of_every_vehicle(self):
        status_by_vehicle_id = {vehicle_id: VehicleStatus.AVAILABLE for vehicle_id in self._list_vehicle_ids()}
        for rental_row in self.database.connection.fetch_all_rows(
            f"SELECT rental_agreement.*, rental_line.vehicle_id "
            f"FROM {self.database.rentals.qualified_table_name} AS rental_line "
            f"JOIN {self.database.rental_agreements.qualified_table_name} AS rental_agreement "
            f"ON rental_agreement.id = rental_line.rental_agreement_id"
        ):
            if self.database.rental_agreements.map_row_to_record(rental_row).is_active_on(self.as_of_date):
                status_by_vehicle_id[rental_row["vehicle_id"]] = VehicleStatus.RENTED
        for sale_row in self.database.connection.fetch_all_rows(
            f"SELECT sale_line.vehicle_id FROM {self.database.sales.qualified_table_name} AS sale_line "
            f"JOIN {self.database.sale_agreements.qualified_table_name} AS sale_agreement "
            f"ON sale_agreement.id = sale_line.sale_agreement_id WHERE sale_agreement.sale_date <= ?",
            (self.as_of_date.isoformat(),),
        ):
            status_by_vehicle_id[sale_row["vehicle_id"]] = VehicleStatus.SOLD
        return status_by_vehicle_id

    def _sum_active_loan_principal_eur(self):
        return self.database.connection.fetch_single_row(
            f"SELECT COALESCE(SUM(principal_eur), 0) FROM {self.database.loans.qualified_table_name} "
            f"WHERE loan_status = 'active'"
        )[0]

    def _list_vehicle_ids(self):
        return [
            vehicle_row["id"]
            for vehicle_row in self.database.connection.fetch_all_rows(
                f"SELECT id FROM {self.database.vehicles.qualified_table_name}"
            )
        ]

    def _count_vehicles(self):
        return max(1, self.database.vehicles.count_all_records())

    @staticmethod
    def _placeholders_for(values):
        return ", ".join("?" for _ in values) or "NULL"
