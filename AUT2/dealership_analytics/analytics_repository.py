import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from enum import StrEnum


class VehicleStatus(StrEnum):
    AVAILABLE = "available"
    RENTED = "rented"
    SOLD = "sold"


class RentalAgreementTerms:
    def __init__(self, rental_agreement):
        self.start_date = date.fromisoformat(rental_agreement["start_date"])
        self.end_date = date.fromisoformat(rental_agreement["end_date"])
        self.auto_prolongation = bool(rental_agreement["auto_prolongation"])
        self.prolongation_period_days = rental_agreement["prolongation_period_days"]
        self.terminated_on = (
            date.fromisoformat(rental_agreement["terminated_on"]) if rental_agreement["terminated_on"] else None
        )

    def is_active_on(self, as_of_date):
        return self.start_date <= as_of_date <= self.effective_end_date_as_of(as_of_date)

    def effective_end_date_as_of(self, as_of_date):
        if not self.auto_prolongation:
            return self.end_date
        prolongation_cutoff_date = as_of_date if self.terminated_on is None else min(as_of_date, self.terminated_on)
        if prolongation_cutoff_date <= self.end_date:
            return self.end_date
        prolongation_count = math.ceil((prolongation_cutoff_date - self.end_date).days / self.prolongation_period_days)
        return self.end_date + timedelta(days=prolongation_count * self.prolongation_period_days)


class DealershipAnalyticsRepository:
    def __init__(self, snapshot_provider, as_of_date):
        self.snapshot_provider = snapshot_provider
        self.as_of_date = as_of_date

    def list_brand_names_with_vehicles(self):
        return sorted({vehicle["brand"] for vehicle in self._snapshot().vehicles})

    def list_engine_types(self):
        return sorted({vehicle["engine"] for vehicle in self._snapshot().vehicles})

    def find_first_and_last_agreement_dates(self):
        snapshot = self._snapshot()
        agreement_dates = [sale_agreement["sale_date"] for sale_agreement in snapshot.sale_agreements] + [
            rental_agreement["start_date"] for rental_agreement in snapshot.rental_agreements
        ]
        if not agreement_dates:
            return self.as_of_date.isoformat(), self.as_of_date.isoformat()
        return min(agreement_dates), max(agreement_dates)

    def summarize_monthly_sales(self, brand_names, first_date, last_date):
        sales_by_month = defaultdict(lambda: {"vehicles_sold": 0, "revenue_eur": 0.0})
        for sale_line, sale_agreement in self._list_sale_lines_matching(brand_names, first_date, last_date):
            month_summary = sales_by_month[sale_agreement["sale_date"][:7]]
            month_summary["vehicles_sold"] += 1
            month_summary["revenue_eur"] += self._discounted_price_eur(sale_line, sale_agreement)
        return [{"month": month, **sales_by_month[month]} for month in sorted(sales_by_month)]

    def summarize_monthly_rental_starts(self, brand_names, first_date, last_date):
        rented_vehicles_by_month = Counter(
            rental_agreement["start_date"][:7]
            for _, rental_agreement in self._list_rental_lines_matching(brand_names, first_date, last_date)
        )
        return [
            {"month": month, "vehicles_rented": rented_vehicles_by_month[month]}
            for month in sorted(rented_vehicles_by_month)
        ]

    def summarize_sales_revenue_by_brand(self, brand_names, first_date, last_date):
        revenue_by_brand = defaultdict(lambda: {"vehicles_sold": 0, "revenue_eur": 0.0})
        for sale_line, sale_agreement in self._list_sale_lines_matching(brand_names, first_date, last_date):
            brand_summary = revenue_by_brand[sale_line["vehicle_brand"]]
            brand_summary["vehicles_sold"] += 1
            brand_summary["revenue_eur"] += self._discounted_price_eur(sale_line, sale_agreement)
        return sorted(
            ({"brand": brand, **summary} for brand, summary in revenue_by_brand.items()),
            key=lambda brand_revenue: brand_revenue["revenue_eur"],
            reverse=True,
        )

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
            "active_loan_principal_eur": sum(
                loan["principal_eur"] for loan in self._snapshot().loans if loan["loan_status"] == "active"
            ),
        }

    def list_stock(self, brand_names, statuses, engine_types):
        status_by_vehicle_id = self._determine_status_of_every_vehicle()
        return [
            {
                "id": vehicle["id"],
                "brand": vehicle["brand"],
                "model": vehicle["model"],
                "manufacture_year": vehicle["manufacture_year"],
                "engine": vehicle["engine"],
                "condition": vehicle["condition"],
                "mileage_km": vehicle["mileage_km"],
                "price_eur": vehicle["price_eur"],
                "daily_rental_rate_eur": vehicle["daily_rental_rate_eur"],
                "status": status_by_vehicle_id[vehicle["id"]].value,
            }
            for vehicle in sorted(self._snapshot().vehicles, key=lambda vehicle: vehicle["id"])
            if vehicle["brand"] in brand_names
            and status_by_vehicle_id[vehicle["id"]] in statuses
            and (not engine_types or vehicle["engine"] in engine_types)
        ]

    def list_loans(self, loan_statuses):
        return [
            {
                "id": loan["id"],
                "lender": loan["lender_name"],
                "lender_type": loan["lender_company_type"],
                "financed_agreement": f"sale {loan['sale_agreement_id']}"
                if loan["sale_agreement_id"] is not None
                else f"rental {loan['rental_agreement_id']}",
                "start_date": loan["start_date"],
                "principal_eur": loan["principal_eur"],
                "annual_interest_rate_pct": loan["annual_interest_rate_pct"],
                "term_months": loan["term_months"],
                "monthly_installment_eur": loan["monthly_installment_eur"],
                "total_interest_eur": round(loan["monthly_installment_eur"] * loan["term_months"] - loan["principal_eur"], 2),
                "loan_status": loan["loan_status"],
            }
            for loan in sorted(self._snapshot().loans, key=lambda loan: loan["id"])
            if loan["loan_status"] in loan_statuses
        ]

    def list_loan_statuses(self):
        return sorted({loan["loan_status"] for loan in self._snapshot().loans})

    def list_factories(self):
        return sorted(self._snapshot().factories, key=lambda factory: factory["id"])

    def list_factory_countries(self):
        return sorted({factory["country"] for factory in self.list_factories()})

    def find_factory_by_id(self, factory_id):
        return next((factory for factory in self.list_factories() if factory["id"] == factory_id), None)

    def find_earliest_factory_opening_year(self):
        return min((factory["opened_year"] for factory in self.list_factories()), default=self.as_of_date.year)

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

    def _snapshot(self):
        return self.snapshot_provider.current_snapshot()

    def _list_sale_lines_matching(self, brand_names, first_date, last_date):
        snapshot = self._snapshot()
        sale_agreements_by_id = {sale_agreement["id"]: sale_agreement for sale_agreement in snapshot.sale_agreements}
        return [
            (sale_line, sale_agreements_by_id[sale_line["sale_agreement_id"]])
            for sale_line in snapshot.sales
            if sale_line["vehicle_brand"] in brand_names
            and first_date <= sale_agreements_by_id[sale_line["sale_agreement_id"]]["sale_date"] <= last_date
        ]

    def _list_rental_lines_matching(self, brand_names, first_date, last_date):
        snapshot = self._snapshot()
        rental_agreements_by_id = {rental_agreement["id"]: rental_agreement for rental_agreement in snapshot.rental_agreements}
        return [
            (rental_line, rental_agreements_by_id[rental_line["rental_agreement_id"]])
            for rental_line in snapshot.rentals
            if rental_line["vehicle_brand"] in brand_names
            and first_date <= rental_agreements_by_id[rental_line["rental_agreement_id"]]["start_date"] <= last_date
        ]

    def _determine_status_of_every_vehicle(self):
        snapshot = self._snapshot()
        status_by_vehicle_id = {vehicle["id"]: VehicleStatus.AVAILABLE for vehicle in snapshot.vehicles}
        rental_agreements_by_id = {rental_agreement["id"]: rental_agreement for rental_agreement in snapshot.rental_agreements}
        for rental_line in snapshot.rentals:
            rental_terms = RentalAgreementTerms(rental_agreements_by_id[rental_line["rental_agreement_id"]])
            if rental_terms.is_active_on(self.as_of_date) and rental_line["vehicle_id"] in status_by_vehicle_id:
                status_by_vehicle_id[rental_line["vehicle_id"]] = VehicleStatus.RENTED
        sale_agreements_by_id = {sale_agreement["id"]: sale_agreement for sale_agreement in snapshot.sale_agreements}
        for sale_line in snapshot.sales:
            sale_date = sale_agreements_by_id[sale_line["sale_agreement_id"]]["sale_date"]
            if sale_date <= self.as_of_date.isoformat() and sale_line["vehicle_id"] in status_by_vehicle_id:
                status_by_vehicle_id[sale_line["vehicle_id"]] = VehicleStatus.SOLD
        return status_by_vehicle_id

    def _list_factories_matching(self, factory_states, countries):
        return [
            factory
            for factory in self.list_factories()
            if ("active" if factory["active"] else "closed") in factory_states
            and (not countries or factory["country"] in countries)
        ]

    @staticmethod
    def _discounted_price_eur(sale_line, sale_agreement):
        return sale_line["price_eur"] * (100 - sale_agreement["discount_pct"]) / 100

    @staticmethod
    def _factory_operated_in_year(factory, year):
        return factory["opened_year"] <= year and (factory["closed_year"] is None or factory["closed_year"] >= year)
