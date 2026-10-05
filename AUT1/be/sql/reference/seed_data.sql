INSERT INTO reference.customers (customer_type, name, address) VALUES
    ('individual', 'Anna Kowalska', 'ul. Marszalkowska 10, Warsaw'),
    ('individual', 'John Smith', '221B Baker Street, London'),
    ('individual', 'Maria Garcia', 'Calle Mayor 5, Madrid'),
    ('individual', 'Hans Mueller', 'Hauptstrasse 12, Berlin'),
    ('individual', 'Sophie Martin', '12 Rue de Rivoli, Paris'),
    ('individual', 'Luca Rossi', 'Via Roma 3, Rome'),
    ('individual', 'Eva Novak', 'Vaclavske namesti 1, Prague'),
    ('individual', 'Piotr Nowak', 'ul. Florianska 7, Krakow'),
    ('individual', 'Emma Johansson', 'Drottninggatan 20, Stockholm'),
    ('individual', 'Liam O''Brien', '14 Grafton Street, Dublin'),
    ('individual', 'Olga Ivanova', 'Nevsky Prospekt 30, Tallinn'),
    ('individual', 'Tomas Horvat', 'Ilica 15, Zagreb'),
    ('institutional', 'CityShare Mobility Sp. z o.o.', 'ul. Grzybowska 62, Warsaw'),
    ('institutional', 'Nordic Utilities AB', 'Sveavagen 44, Stockholm'),
    ('institutional', 'GreenRoute Logistics GmbH', 'Hafenstrasse 9, Hamburg'),
    ('institutional', 'Metro Taxi Cooperative', 'Via Torino 18, Milan'),
    ('institutional', 'Apex Consulting Group Ltd', '10 Canary Wharf, London');

INSERT INTO reference.individual_customers (customer_id, customer_type, date_of_birth) VALUES
    (1, 'individual', '1965-06-12'),
    (2, 'individual', '1972-11-23'),
    (3, 'individual', '1979-04-06'),
    (4, 'individual', '1986-09-17'),
    (5, 'individual', '1993-02-28'),
    (6, 'individual', '1960-07-11'),
    (7, 'individual', '1967-12-22'),
    (8, 'individual', '1974-05-05'),
    (9, 'individual', '1981-10-16'),
    (10, 'individual', '1988-03-27'),
    (11, 'individual', '1995-08-10'),
    (12, 'individual', '1962-01-21');

INSERT INTO reference.institutional_customers (customer_id, customer_type, tax_id, company_registration_number, contact_person, negotiated_fleet_discount_pct) VALUES
    (13, 'institutional', 'PL5272899999', 'KRS0000654321', 'Marta Wisniewska', NULL),
    (14, 'institutional', 'SE556677889901', '556677-8899', 'Erik Lindqvist', 15),
    (15, 'institutional', 'DE298765432', 'HRB 154321', 'Jonas Becker', 12),
    (16, 'institutional', 'IT09876543210', 'MI-2098765', 'Giulia Bianchi', NULL),
    (17, 'institutional', 'GB123456789', '09876543', 'Oliver Hughes', NULL);

INSERT INTO reference.companies (name, company_type, tax_id, address) VALUES
    ('Northbridge Bank', 'bank', 'PL5251234567', 'ul. Prosta 51, Warsaw'),
    ('Alpine Credit Bank', 'bank', 'ATU12345678', 'Kaerntner Strasse 21, Vienna'),
    ('Baltic Savings Bank', 'bank', 'EE100234567', 'Narva mnt 7, Tallinn'),
    ('EuroDrive Leasing', 'leasing_company', 'DE811234567', 'Friedrichstrasse 88, Berlin'),
    ('Motion Auto Finance', 'leasing_company', 'FR40123456789', '45 Avenue de la Grande Armee, Paris'),
    ('Velo Fleet Leasing', 'leasing_company', 'NL812345678B01', 'Herengracht 120, Amsterdam');

INSERT INTO reference.commercial_policy (id, fleet_minimum_vehicle_count, default_fleet_discount_pct, default_prolongation_period_days) VALUES
    (1, 10, 10, 30);
