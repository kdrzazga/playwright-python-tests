import math
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class EngineType(StrEnum):
    DIESEL = "diesel"
    OIL = "oil"
    ELECTRIC = "electric"


class BodyStyle(StrEnum):
    SEDAN = "sedan"
    SUV = "suv"
    HATCHBACK = "hatchback"
    ESTATE = "estate"
    COUPE = "coupe"
    CONVERTIBLE = "convertible"
    PICKUP = "pickup"
    VAN = "van"


class Transmission(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class Drivetrain(StrEnum):
    FWD = "FWD"
    RWD = "RWD"
    AWD = "AWD"
    FOUR_WHEEL_DRIVE = "4WD"


class VehicleCondition(StrEnum):
    NEW = "new"
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class CompanyType(StrEnum):
    BANK = "bank"
    LEASING_COMPANY = "leasing_company"


class CustomerType(StrEnum):
    INDIVIDUAL = "individual"
    INSTITUTIONAL = "institutional"


class UserRole(StrEnum):
    ADMIN = "admin"
    SUPERUSER = "superuser"
    DEALER = "dealer"
    VIEWER = "viewer"


class PermissionName(StrEnum):
    VIEW_DB_TABLES = "view_db_tables"
    FRONTEND_ACCESS = "frontend.access"
    VEHICLE_VIEW = "vehicle.view"
    VEHICLE_ADD = "vehicle.add"
    VEHICLE_MODIFY = "vehicle.modify"
    VEHICLE_REMOVE = "vehicle.remove"
    RENTAL_VIEW = "rental.view"
    RENTAL_ADD = "rental.add"
    RENTAL_MODIFY = "rental.modify"
    RENTAL_REMOVE = "rental.remove"
    SELL_VIEW = "sell.view"
    SELL_ADD = "sell.add"
    SELL_MODIFY = "sell.modify"
    SELL_REMOVE = "sell.remove"
    LOAN_VIEW = "loan.view"
    LOAN_ADD = "loan.add"
    LOAN_MODIFY = "loan.modify"
    LOAN_REMOVE = "loan.remove"
    BRAND_VW_ACCESS = "brand.vw.access"
    BRAND_TOYOTA_ACCESS = "brand.toyota.access"
    BRAND_MERCEDES_ACCESS = "brand.mercedes.access"
    BRAND_TESLA_ACCESS = "brand.tesla.access"
    BRAND_SKODA_ACCESS = "brand.skoda.access"
    BRAND_BMW_ACCESS = "brand.bmw.access"


class LoanStatus(StrEnum):
    ACTIVE = "active"
    REPAID = "repaid"
    DEFAULTED = "defaulted"


@dataclass(frozen=True)
class Vehicle:
    id: int
    brand: str
    model: str
    engine: EngineType
    manufacture_year: int
    used: bool
    body_style: BodyStyle
    transmission: Transmission
    drivetrain: Drivetrain
    power_hp: int
    torque_nm: int
    number_of_doors: int
    number_of_seats: int
    color: str
    mileage_km: int
    vin: str
    registration: str | None
    condition: VehicleCondition
    price_eur: int
    daily_rental_rate_eur: int


@dataclass(frozen=True)
class Customer:
    id: int
    customer_type: CustomerType
    name: str
    address: str

    @property
    def is_institutional(self):
        return self.customer_type is CustomerType.INSTITUTIONAL


@dataclass(frozen=True)
class IndividualCustomer:
    customer_id: int
    customer_type: CustomerType
    date_of_birth: date


@dataclass(frozen=True)
class InstitutionalCustomer:
    customer_id: int
    customer_type: CustomerType
    tax_id: str
    company_registration_number: str
    contact_person: str
    negotiated_fleet_discount_pct: int | None


@dataclass(frozen=True)
class Company:
    id: int
    name: str
    company_type: CompanyType
    tax_id: str
    address: str


@dataclass(frozen=True)
class Factory:
    id: int
    name: str
    manufacturer: str
    city: str
    country: str
    opened_year: int
    closed_year: int | None
    active: bool
    latitude: float
    longitude: float


@dataclass(frozen=True)
class CommercialPolicy:
    id: int
    fleet_minimum_vehicle_count: int
    default_fleet_discount_pct: int
    default_prolongation_period_days: int

    def qualifies_as_fleet(self, vehicle_count):
        return vehicle_count >= self.fleet_minimum_vehicle_count


@dataclass(frozen=True)
class OccupationPeriod:
    first_day: date
    last_day: date | None

    @property
    def is_open_ended(self):
        return self.last_day is None

    def overlaps(self, other_period):
        this_starts_before_other_ends = other_period.is_open_ended or self.first_day <= other_period.last_day
        other_starts_before_this_ends = self.is_open_ended or other_period.first_day <= self.last_day
        return this_starts_before_other_ends and other_starts_before_this_ends

    def describe(self):
        return f"{self.first_day.isoformat()} - {'open-ended' if self.is_open_ended else self.last_day.isoformat()}"


@dataclass(frozen=True)
class SaleAgreement:
    id: int
    customer_id: int
    customer_type: CustomerType
    sale_date: date
    discount_pct: int

    def occupation_period(self):
        return OccupationPeriod(self.sale_date, None)


@dataclass(frozen=True)
class Sale:
    id: int
    sale_agreement_id: int
    vehicle_id: int
    price_eur: int


@dataclass(frozen=True)
class RentalAgreement:
    id: int
    customer_id: int
    customer_type: CustomerType
    start_date: date
    end_date: date
    auto_prolongation: bool
    prolongation_period_days: int
    terminated_on: date | None
    discount_pct: int

    def effective_end_date_as_of(self, as_of_date):
        if not self.auto_prolongation:
            return self.end_date
        prolongation_cutoff_date = as_of_date if self.terminated_on is None else min(as_of_date, self.terminated_on)
        if prolongation_cutoff_date <= self.end_date:
            return self.end_date
        days_past_original_end = (prolongation_cutoff_date - self.end_date).days
        prolongation_count = math.ceil(days_past_original_end / self.prolongation_period_days)
        return self.end_date + timedelta(days=prolongation_count * self.prolongation_period_days)

    def is_active_on(self, as_of_date):
        return self.start_date <= as_of_date <= self.effective_end_date_as_of(as_of_date)

    def occupation_period(self):
        if not self.auto_prolongation:
            return OccupationPeriod(self.start_date, self.end_date)
        if self.terminated_on is None:
            return OccupationPeriod(self.start_date, None)
        return OccupationPeriod(self.start_date, self.effective_end_date_as_of(self.terminated_on))


@dataclass(frozen=True)
class Rental:
    id: int
    rental_agreement_id: int
    vehicle_id: int
    daily_rate_eur: int


@dataclass(frozen=True)
class Loan:
    id: int
    lender_company_id: int
    lender_company_type: CompanyType
    sale_agreement_id: int | None
    rental_agreement_id: int | None
    start_date: date
    financed_amount_eur: int
    down_payment_eur: int
    principal_eur: int
    annual_interest_rate_pct: float
    term_months: int
    monthly_installment_eur: float
    loan_status: LoanStatus

    @property
    def finances_sale(self):
        return self.sale_agreement_id is not None

    def total_of_all_installments_eur(self):
        return round(self.monthly_installment_eur * self.term_months, 2)

    def total_interest_eur(self):
        return round(self.total_of_all_installments_eur() - self.principal_eur, 2)


@dataclass(frozen=True)
class UserAccount:
    id: int
    username: str
    password_hash: str
    role: UserRole
    name: str
    last_name: str
    company_id: int | None


@dataclass(frozen=True)
class PermissionDefinition:
    id: int
    permission: str
    brand_id: int | None


@dataclass(frozen=True)
class Brand:
    id: int
    code: str
    name: str


@dataclass(frozen=True)
class RolePermissionRule:
    id: int
    role: UserRole
    permission_pattern: str


@dataclass(frozen=True)
class UserPermission:
    id: int
    user_id: int
    permission_id: int
