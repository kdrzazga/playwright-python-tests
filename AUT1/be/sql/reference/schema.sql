CREATE TABLE reference.customers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_type TEXT NOT NULL CHECK (customer_type IN ('individual', 'institutional')),
    name          TEXT NOT NULL,
    address       TEXT NOT NULL,
    UNIQUE (id, customer_type)
);

CREATE TABLE reference.individual_customers (
    customer_id   INTEGER PRIMARY KEY,
    customer_type TEXT NOT NULL DEFAULT 'individual' CHECK (customer_type = 'individual'),
    date_of_birth TEXT NOT NULL CHECK (date(date_of_birth) = date_of_birth),
    FOREIGN KEY (customer_id, customer_type) REFERENCES customers (id, customer_type)
);

CREATE TABLE reference.institutional_customers (
    customer_id                   INTEGER PRIMARY KEY,
    customer_type                 TEXT NOT NULL DEFAULT 'institutional' CHECK (customer_type = 'institutional'),
    tax_id                        TEXT NOT NULL UNIQUE,
    company_registration_number   TEXT NOT NULL UNIQUE,
    contact_person                TEXT NOT NULL,
    negotiated_fleet_discount_pct INTEGER CHECK (negotiated_fleet_discount_pct BETWEEN 0 AND 50),
    FOREIGN KEY (customer_id, customer_type) REFERENCES customers (id, customer_type)
);

CREATE TABLE reference.companies (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    company_type TEXT NOT NULL CHECK (company_type IN ('bank', 'leasing_company')),
    tax_id       TEXT NOT NULL UNIQUE,
    address      TEXT NOT NULL,
    UNIQUE (id, company_type)
);

CREATE TABLE reference.commercial_policy (
    id                               INTEGER PRIMARY KEY CHECK (id = 1),
    fleet_minimum_vehicle_count      INTEGER NOT NULL CHECK (fleet_minimum_vehicle_count >= 2),
    default_fleet_discount_pct       INTEGER NOT NULL CHECK (default_fleet_discount_pct BETWEEN 0 AND 50),
    default_prolongation_period_days INTEGER NOT NULL CHECK (default_prolongation_period_days > 0)
);

CREATE TABLE reference.factories (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    manufacturer TEXT    NOT NULL,
    city         TEXT    NOT NULL,
    country      TEXT    NOT NULL,
    opened_year  INTEGER NOT NULL CHECK (opened_year BETWEEN 1880 AND 2100),
    closed_year  INTEGER CHECK (closed_year IS NULL OR closed_year >= opened_year),
    active       BOOLEAN NOT NULL CHECK (active IN (0, 1)),
    CHECK ((active = 1) = (closed_year IS NULL))
);
