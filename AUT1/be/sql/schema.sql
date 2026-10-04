CREATE TABLE vehicles (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    brand            TEXT    NOT NULL,
    model            TEXT    NOT NULL,
    engine           TEXT    NOT NULL CHECK (engine IN ('diesel', 'oil', 'electric')),
    manufacture_year INTEGER NOT NULL,
    used             BOOLEAN NOT NULL CHECK (used IN (0, 1))
);

CREATE TABLE customers (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    address TEXT NOT NULL
);

CREATE TABLE sales (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id  INTEGER NOT NULL REFERENCES vehicles (id),
    customer_id INTEGER NOT NULL REFERENCES customers (id)
);

CREATE TABLE rentals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id  INTEGER NOT NULL REFERENCES vehicles (id),
    customer_id INTEGER NOT NULL REFERENCES customers (id)
);
