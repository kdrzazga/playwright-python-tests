from database_errors import RecordNotFoundError
from records import CompanyType, LoanStatus, OccupationPeriod
from simulated_load import subject_to_simulated_load


class EmptyVehicleSelectionError(ValueError):
    pass


class DuplicateVehicleSelectionError(ValueError):
    pass


class FinancingRejectedError(ValueError):
    pass


class VehicleUnavailableError(ValueError):
    def __init__(self, conflict_descriptions):
        super().__init__("; ".join(conflict_descriptions))
        self.conflict_descriptions = conflict_descriptions


class VehicleAvailabilityChecker:
    def __init__(self, database):
        self.database = database

    def ensure_vehicles_available_within_transaction(self, transaction, vehicle_ids, requested_period):
        conflict_descriptions = [
            f"Vehicle {vehicle_id} is already {occupation_kind} under agreement {agreement_id} "
            f"({occupied_period.describe()}), which overlaps the requested period ({requested_period.describe()})"
            for vehicle_id, occupation_kind, agreement_id, occupied_period in self._find_existing_occupations(
                transaction, vehicle_ids
            )
            if occupied_period.overlaps(requested_period)
        ]
        if conflict_descriptions:
            raise VehicleUnavailableError(conflict_descriptions)

    def _find_existing_occupations(self, transaction, vehicle_ids):
        vehicle_id_placeholders = ", ".join("?" for _ in vehicle_ids)
        rental_rows = transaction.execute(
            f"SELECT rental_agreement.*, rental_line.vehicle_id "
            f"FROM {self.database.rentals.qualified_table_name} AS rental_line "
            f"JOIN {self.database.rental_agreements.qualified_table_name} AS rental_agreement "
            f"ON rental_agreement.id = rental_line.rental_agreement_id "
            f"WHERE rental_line.vehicle_id IN ({vehicle_id_placeholders}) "
            f"ORDER BY rental_line.vehicle_id, rental_agreement.id",
            tuple(vehicle_ids),
        ).fetchall()
        for rental_row in rental_rows:
            rental_agreement = self.database.rental_agreements.map_row_to_record(rental_row)
            yield rental_row["vehicle_id"], "rented", rental_agreement.id, rental_agreement.occupation_period()
        sale_rows = transaction.execute(
            f"SELECT sale_agreement.*, sale_line.vehicle_id "
            f"FROM {self.database.sales.qualified_table_name} AS sale_line "
            f"JOIN {self.database.sale_agreements.qualified_table_name} AS sale_agreement "
            f"ON sale_agreement.id = sale_line.sale_agreement_id "
            f"WHERE sale_line.vehicle_id IN ({vehicle_id_placeholders}) "
            f"ORDER BY sale_line.vehicle_id",
            tuple(vehicle_ids),
        ).fetchall()
        for sale_row in sale_rows:
            sale_agreement = self.database.sale_agreements.map_row_to_record(sale_row)
            yield sale_row["vehicle_id"], "sold", sale_agreement.id, sale_agreement.occupation_period()


class DatabaseBackedService:
    @property
    def simulated_load(self):
        return self.database.simulated_load

    @property
    def touches_reference_data(self):
        return False


class FleetDiscountCalculator(DatabaseBackedService):
    def __init__(self, database, commercial_policy_id=1):
        self.database = database
        self.commercial_policy_id = commercial_policy_id

    @subject_to_simulated_load
    def load_commercial_policy(self):
        return self.database.commercial_policy.find_record_by_id(self.commercial_policy_id)

    @subject_to_simulated_load
    def determine_discount_pct(self, customer, vehicle_count):
        commercial_policy = self.load_commercial_policy()
        if not customer.is_institutional or not commercial_policy.qualifies_as_fleet(vehicle_count):
            return 0
        institutional_customer = self.database.institutional_customers.find_record_by_id(customer.id)
        if institutional_customer.negotiated_fleet_discount_pct is not None:
            return institutional_customer.negotiated_fleet_discount_pct
        return commercial_policy.default_fleet_discount_pct


class AgreementDesk(DatabaseBackedService):
    def __init__(self, database, fleet_discount_calculator, vehicle_availability_checker):
        self.database = database
        self.fleet_discount_calculator = fleet_discount_calculator
        self.vehicle_availability_checker = vehicle_availability_checker

    def _load_existing_customer(self, customer_id):
        customer = self.database.customers.find_record_by_id(customer_id)
        if customer is None:
            raise RecordNotFoundError(f"No customer with id {customer_id}")
        return customer

    @staticmethod
    def _ensure_vehicle_selection_is_valid(vehicle_ids):
        if not vehicle_ids:
            raise EmptyVehicleSelectionError("An agreement needs at least one vehicle")
        if len(set(vehicle_ids)) != len(vehicle_ids):
            raise DuplicateVehicleSelectionError("Each vehicle can appear only once in an agreement")

    def _insert_agreement_line_copying_vehicle_column(
        self, transaction, line_table, agreement_foreign_key_column_name, agreement_id, vehicle_id, copied_columns
    ):
        line_column_names = (agreement_foreign_key_column_name, "vehicle_id", *copied_columns)
        vehicle_column_names = ("id", *copied_columns.values())
        inserted_row_count = transaction.execute(
            f"INSERT INTO {line_table.qualified_table_name} ({', '.join(line_column_names)}) "
            f"SELECT ?, {', '.join(vehicle_column_names)} FROM {self.database.vehicles.qualified_table_name} WHERE id = ?",
            (agreement_id, vehicle_id),
        ).rowcount
        if inserted_row_count == 0:
            raise RecordNotFoundError(f"No vehicle with id {vehicle_id}")

    @staticmethod
    def _apply_discount(amount_eur, discount_pct):
        return round(amount_eur * (100 - discount_pct) / 100)


class SalesDesk(AgreementDesk):
    @subject_to_simulated_load
    def sell_vehicles_to_customer(self, customer_id, vehicle_ids, sale_date):
        self._ensure_vehicle_selection_is_valid(vehicle_ids)
        customer = self._load_existing_customer(customer_id)
        discount_pct = self.fleet_discount_calculator.determine_discount_pct(customer, len(vehicle_ids))
        agreement_columns = {
            "customer_id": customer.id,
            "customer_type": customer.customer_type.value,
            "sale_date": sale_date.isoformat(),
            "discount_pct": discount_pct,
        }

        requested_period = OccupationPeriod(sale_date, None)

        def create_sale_agreement_with_one_line_per_vehicle(transaction):
            self.vehicle_availability_checker.ensure_vehicles_available_within_transaction(
                transaction, vehicle_ids, requested_period
            )
            sale_agreement_id = transaction.execute(
                self.database.sale_agreements.build_insert_statement(tuple(agreement_columns)),
                tuple(agreement_columns.values()),
            ).lastrowid
            for vehicle_id in vehicle_ids:
                self._insert_agreement_line_copying_vehicle_column(
                    transaction, self.database.sales, "sale_agreement_id", sale_agreement_id, vehicle_id,
                    {"price_eur": "price_eur"},
                )
            return sale_agreement_id

        sale_agreement_id = self.database.connection.run_in_single_transaction(
            create_sale_agreement_with_one_line_per_vehicle
        )
        return self.database.sale_agreements.find_record_by_id(sale_agreement_id)

    @subject_to_simulated_load
    def calculate_total_price_after_discount_eur(self, sale_agreement_id):
        sale_agreement = self.database.sale_agreements.find_record_by_id(sale_agreement_id)
        total_list_price_eur = self.database.connection.fetch_single_row(
            f"SELECT COALESCE(SUM(price_eur), 0) FROM {self.database.sales.qualified_table_name} WHERE sale_agreement_id = ?",
            (sale_agreement_id,),
        )[0]
        return self._apply_discount(total_list_price_eur, sale_agreement.discount_pct)


class RentalDesk(AgreementDesk):
    @subject_to_simulated_load
    def rent_vehicles_to_customer(
        self,
        customer_id,
        vehicle_ids,
        start_date,
        end_date,
        auto_prolongation=True,
        prolongation_period_days=None,
    ):
        self._ensure_vehicle_selection_is_valid(vehicle_ids)
        customer = self._load_existing_customer(customer_id)
        discount_pct = self.fleet_discount_calculator.determine_discount_pct(customer, len(vehicle_ids))
        if prolongation_period_days is None:
            prolongation_period_days = (
                self.fleet_discount_calculator.load_commercial_policy().default_prolongation_period_days
            )
        agreement_columns = {
            "customer_id": customer.id,
            "customer_type": customer.customer_type.value,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "auto_prolongation": auto_prolongation,
            "prolongation_period_days": prolongation_period_days,
            "discount_pct": discount_pct,
        }

        requested_period = OccupationPeriod(start_date, None if auto_prolongation else end_date)

        def create_rental_agreement_with_one_line_per_vehicle(transaction):
            self.vehicle_availability_checker.ensure_vehicles_available_within_transaction(
                transaction, vehicle_ids, requested_period
            )
            rental_agreement_id = transaction.execute(
                self.database.rental_agreements.build_insert_statement(tuple(agreement_columns)),
                tuple(agreement_columns.values()),
            ).lastrowid
            for vehicle_id in vehicle_ids:
                self._insert_agreement_line_copying_vehicle_column(
                    transaction, self.database.rentals, "rental_agreement_id", rental_agreement_id, vehicle_id,
                    {"daily_rate_eur": "daily_rental_rate_eur"},
                )
            return rental_agreement_id

        rental_agreement_id = self.database.connection.run_in_single_transaction(
            create_rental_agreement_with_one_line_per_vehicle
        )
        return self.database.rental_agreements.find_record_by_id(rental_agreement_id)

    @subject_to_simulated_load
    def terminate_rental_agreement(self, rental_agreement_id, terminated_on):
        return self.database.rental_agreements.update_record_by_primary_key(
            rental_agreement_id, terminated_on=terminated_on.isoformat()
        )

    @subject_to_simulated_load
    def calculate_daily_total_after_discount_eur(self, rental_agreement_id):
        rental_agreement = self.database.rental_agreements.find_record_by_id(rental_agreement_id)
        total_daily_rate_eur = self.database.connection.fetch_single_row(
            f"SELECT COALESCE(SUM(daily_rate_eur), 0) FROM {self.database.rentals.qualified_table_name} "
            f"WHERE rental_agreement_id = ?",
            (rental_agreement_id,),
        )[0]
        return self._apply_discount(total_daily_rate_eur, rental_agreement.discount_pct)

    @subject_to_simulated_load
    def calculate_initial_term_cost_after_discount_eur(self, rental_agreement_id):
        rental_agreement = self.database.rental_agreements.find_record_by_id(rental_agreement_id)
        initial_term_days = (rental_agreement.end_date - rental_agreement.start_date).days + 1
        return self.calculate_daily_total_after_discount_eur(rental_agreement_id) * initial_term_days


class AnnuityInstallmentCalculator:
    def calculate_monthly_installment_eur(self, principal_eur, annual_interest_rate_pct, term_months):
        monthly_interest_rate = annual_interest_rate_pct / 100 / 12
        if monthly_interest_rate == 0:
            return round(principal_eur / term_months, 2)
        return round(principal_eur * monthly_interest_rate / (1 - (1 + monthly_interest_rate) ** -term_months), 2)


class LoanDesk(DatabaseBackedService):
    def __init__(self, database, sales_desk, rental_desk, installment_calculator):
        self.database = database
        self.sales_desk = sales_desk
        self.rental_desk = rental_desk
        self.installment_calculator = installment_calculator
        self.lender_type_allowed_by_agreement_column_name = {
            "sale_agreement_id": CompanyType.BANK,
            "rental_agreement_id": CompanyType.LEASING_COMPANY,
        }

    @subject_to_simulated_load
    def finance_sale_agreement(
        self, sale_agreement_id, lender_company_id, start_date, annual_interest_rate_pct, term_months, down_payment_eur=0
    ):
        sale_agreement = self._load_existing_record(self.database.sale_agreements, sale_agreement_id, "sale agreement")
        return self._grant_loan(
            "sale_agreement_id",
            sale_agreement_id,
            sale_agreement.sale_date,
            self.sales_desk.calculate_total_price_after_discount_eur(sale_agreement_id),
            lender_company_id,
            start_date,
            annual_interest_rate_pct,
            term_months,
            down_payment_eur,
        )

    @subject_to_simulated_load
    def finance_rental_agreement(
        self, rental_agreement_id, lender_company_id, start_date, annual_interest_rate_pct, term_months, down_payment_eur=0
    ):
        rental_agreement = self._load_existing_record(
            self.database.rental_agreements, rental_agreement_id, "rental agreement"
        )
        return self._grant_loan(
            "rental_agreement_id",
            rental_agreement_id,
            rental_agreement.start_date,
            self.rental_desk.calculate_initial_term_cost_after_discount_eur(rental_agreement_id),
            lender_company_id,
            start_date,
            annual_interest_rate_pct,
            term_months,
            down_payment_eur,
        )

    @subject_to_simulated_load
    def mark_loan_repaid(self, loan_id):
        return self.database.loans.update_record_by_primary_key(loan_id, loan_status=LoanStatus.REPAID.value)

    @subject_to_simulated_load
    def mark_loan_defaulted(self, loan_id):
        return self.database.loans.update_record_by_primary_key(loan_id, loan_status=LoanStatus.DEFAULTED.value)

    def _grant_loan(
        self,
        agreement_column_name,
        agreement_id,
        agreement_date,
        financed_amount_eur,
        lender_company_id,
        start_date,
        annual_interest_rate_pct,
        term_months,
        down_payment_eur,
    ):
        lender_company = self._load_existing_record(self.database.companies, lender_company_id, "lender company")
        self._ensure_lender_type_may_finance_agreement_type(lender_company, agreement_column_name)
        self._ensure_agreement_not_financed_yet(agreement_column_name, agreement_id)
        if start_date < agreement_date:
            raise FinancingRejectedError(
                f"Loan cannot start on {start_date.isoformat()}, before the agreement date {agreement_date.isoformat()}"
            )
        if not 0 <= down_payment_eur < financed_amount_eur:
            raise FinancingRejectedError(
                f"Down payment must be at least 0 and less than the financed amount of {financed_amount_eur} EUR"
            )
        principal_eur = financed_amount_eur - down_payment_eur
        return self.database.loans.insert_record_with_generated_id(
            lender_company_id=lender_company_id,
            lender_company_type=lender_company.company_type.value,
            **{agreement_column_name: agreement_id},
            start_date=start_date.isoformat(),
            financed_amount_eur=financed_amount_eur,
            down_payment_eur=down_payment_eur,
            principal_eur=principal_eur,
            annual_interest_rate_pct=annual_interest_rate_pct,
            term_months=term_months,
            monthly_installment_eur=self.installment_calculator.calculate_monthly_installment_eur(
                principal_eur, annual_interest_rate_pct, term_months
            ),
            loan_status=LoanStatus.ACTIVE.value,
        )

    def _ensure_lender_type_may_finance_agreement_type(self, lender_company, agreement_column_name):
        allowed_lender_type = self.lender_type_allowed_by_agreement_column_name[agreement_column_name]
        if lender_company.company_type is not allowed_lender_type:
            financed_agreement_kind = agreement_column_name.removesuffix("_agreement_id")
            raise FinancingRejectedError(
                f"{lender_company.name} is a {lender_company.company_type.value} and cannot finance "
                f"{financed_agreement_kind}s; only a {allowed_lender_type.value} can"
            )

    def _ensure_agreement_not_financed_yet(self, agreement_column_name, agreement_id):
        existing_loan_row = self.database.connection.fetch_single_row(
            f"SELECT id FROM {self.database.loans.qualified_table_name} WHERE {agreement_column_name} = ?",
            (agreement_id,),
        )
        if existing_loan_row is not None:
            raise FinancingRejectedError(
                f"Agreement {agreement_id} is already financed by loan {existing_loan_row['id']}"
            )

    @staticmethod
    def _load_existing_record(table, record_id, record_description):
        record = table.find_record_by_id(record_id)
        if record is None:
            raise RecordNotFoundError(f"No {record_description} with id {record_id}")
        return record
