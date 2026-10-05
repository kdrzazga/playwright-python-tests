CREATE TABLE dealership.vehicles (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    brand                 TEXT    NOT NULL,
    model                 TEXT    NOT NULL,
    engine                TEXT    NOT NULL CHECK (engine IN ('diesel', 'oil', 'electric')),
    manufacture_year      INTEGER NOT NULL,
    used                  BOOLEAN NOT NULL CHECK (used IN (0, 1)),
    body_style            TEXT    NOT NULL CHECK (body_style IN ('sedan', 'suv', 'hatchback', 'estate', 'coupe', 'convertible', 'pickup', 'van')),
    transmission          TEXT    NOT NULL CHECK (transmission IN ('automatic', 'manual')),
    drivetrain            TEXT    NOT NULL CHECK (drivetrain IN ('FWD', 'RWD', 'AWD', '4WD')),
    power_hp              INTEGER NOT NULL CHECK (power_hp > 0),
    torque_nm             INTEGER NOT NULL CHECK (torque_nm > 0),
    number_of_doors       INTEGER NOT NULL CHECK (number_of_doors BETWEEN 2 AND 5),
    number_of_seats       INTEGER NOT NULL CHECK (number_of_seats BETWEEN 1 AND 9),
    color                 TEXT    NOT NULL,
    mileage_km            INTEGER NOT NULL CHECK (mileage_km >= 0),
    vin                   TEXT    NOT NULL UNIQUE CHECK (length(vin) = 17),
    registration          TEXT    UNIQUE,
    condition             TEXT    NOT NULL CHECK (condition IN ('new', 'excellent', 'good', 'fair', 'poor')),
    price_eur             INTEGER NOT NULL CHECK (price_eur > 0),
    daily_rental_rate_eur INTEGER NOT NULL CHECK (daily_rental_rate_eur > 0),
    CHECK ((used = 0) = (condition = 'new'))
);

CREATE TABLE dealership.customers (
    id            INTEGER PRIMARY KEY,
    customer_type TEXT NOT NULL CHECK (customer_type IN ('individual', 'institutional')),
    name          TEXT NOT NULL,
    address       TEXT NOT NULL,
    UNIQUE (id, customer_type)
);

CREATE TABLE dealership.individual_customers (
    customer_id   INTEGER PRIMARY KEY,
    customer_type TEXT NOT NULL CHECK (customer_type = 'individual'),
    date_of_birth TEXT NOT NULL,
    FOREIGN KEY (customer_id, customer_type) REFERENCES customers (id, customer_type)
);

CREATE TABLE dealership.institutional_customers (
    customer_id                   INTEGER PRIMARY KEY,
    customer_type                 TEXT NOT NULL CHECK (customer_type = 'institutional'),
    tax_id                        TEXT NOT NULL UNIQUE,
    company_registration_number   TEXT NOT NULL UNIQUE,
    contact_person                TEXT NOT NULL,
    negotiated_fleet_discount_pct INTEGER,
    FOREIGN KEY (customer_id, customer_type) REFERENCES customers (id, customer_type)
);

CREATE TABLE dealership.companies (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    company_type TEXT NOT NULL CHECK (company_type IN ('bank', 'leasing_company')),
    tax_id       TEXT NOT NULL UNIQUE,
    address      TEXT NOT NULL,
    UNIQUE (id, company_type)
);

CREATE TABLE dealership.commercial_policy (
    id                               INTEGER PRIMARY KEY,
    fleet_minimum_vehicle_count      INTEGER NOT NULL,
    default_fleet_discount_pct       INTEGER NOT NULL,
    default_prolongation_period_days INTEGER NOT NULL
);

CREATE TABLE dealership.replication_guard (
    replication_in_progress INTEGER NOT NULL CHECK (replication_in_progress IN (0, 1))
);

INSERT INTO dealership.replication_guard (replication_in_progress) VALUES (0);

CREATE TABLE dealership.sale_agreements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id   INTEGER NOT NULL,
    customer_type TEXT    NOT NULL,
    sale_date     TEXT    NOT NULL CHECK (date(sale_date) = sale_date),
    discount_pct  INTEGER NOT NULL DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 50),
    FOREIGN KEY (customer_id, customer_type) REFERENCES customers (id, customer_type),
    CHECK (discount_pct = 0 OR customer_type = 'institutional')
);

CREATE TABLE dealership.sales (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_agreement_id INTEGER NOT NULL REFERENCES sale_agreements (id),
    vehicle_id        INTEGER NOT NULL UNIQUE REFERENCES vehicles (id),
    price_eur         INTEGER NOT NULL CHECK (price_eur > 0)
);

CREATE TABLE dealership.rental_agreements (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id              INTEGER NOT NULL,
    customer_type            TEXT    NOT NULL,
    start_date               TEXT    NOT NULL CHECK (date(start_date) = start_date),
    end_date                 TEXT    NOT NULL CHECK (date(end_date) = end_date),
    auto_prolongation        BOOLEAN NOT NULL DEFAULT 1 CHECK (auto_prolongation IN (0, 1)),
    prolongation_period_days INTEGER NOT NULL CHECK (prolongation_period_days > 0),
    terminated_on            TEXT    CHECK (terminated_on IS NULL OR date(terminated_on) = terminated_on),
    discount_pct             INTEGER NOT NULL DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 50),
    FOREIGN KEY (customer_id, customer_type) REFERENCES customers (id, customer_type),
    CHECK (end_date >= start_date),
    CHECK (terminated_on IS NULL OR terminated_on >= start_date),
    CHECK (discount_pct = 0 OR customer_type = 'institutional')
);

CREATE TABLE dealership.rentals (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    rental_agreement_id INTEGER NOT NULL REFERENCES rental_agreements (id),
    vehicle_id          INTEGER NOT NULL REFERENCES vehicles (id),
    daily_rate_eur      INTEGER NOT NULL CHECK (daily_rate_eur > 0),
    UNIQUE (rental_agreement_id, vehicle_id)
);

CREATE TABLE dealership.loans (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    lender_company_id        INTEGER NOT NULL,
    lender_company_type      TEXT    NOT NULL,
    sale_agreement_id        INTEGER UNIQUE REFERENCES sale_agreements (id),
    rental_agreement_id      INTEGER UNIQUE REFERENCES rental_agreements (id),
    start_date               TEXT    NOT NULL CHECK (date(start_date) = start_date),
    financed_amount_eur      INTEGER NOT NULL CHECK (financed_amount_eur > 0),
    down_payment_eur         INTEGER NOT NULL DEFAULT 0 CHECK (down_payment_eur >= 0),
    principal_eur            INTEGER NOT NULL CHECK (principal_eur > 0),
    annual_interest_rate_pct REAL    NOT NULL CHECK (annual_interest_rate_pct BETWEEN 0 AND 30),
    term_months              INTEGER NOT NULL CHECK (term_months BETWEEN 6 AND 96),
    monthly_installment_eur  REAL    NOT NULL CHECK (monthly_installment_eur > 0),
    loan_status              TEXT    NOT NULL DEFAULT 'active' CHECK (loan_status IN ('active', 'repaid', 'defaulted')),
    FOREIGN KEY (lender_company_id, lender_company_type) REFERENCES companies (id, company_type),
    CHECK ((sale_agreement_id IS NULL) <> (rental_agreement_id IS NULL)),
    CHECK (principal_eur = financed_amount_eur - down_payment_eur),
    CHECK (
        (lender_company_type = 'bank' AND sale_agreement_id IS NOT NULL)
        OR (lender_company_type = 'leasing_company' AND rental_agreement_id IS NOT NULL)
    )
);
