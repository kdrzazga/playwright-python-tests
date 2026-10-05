CREATE TABLE security.companies (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    company_type TEXT NOT NULL CHECK (company_type IN ('bank', 'leasing_company')),
    tax_id       TEXT NOT NULL UNIQUE,
    address      TEXT NOT NULL,
    UNIQUE (id, company_type)
);

CREATE TABLE security.brands (
    id   INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE CHECK (code <> '' AND code NOT GLOB '*[^a-z0-9]*'),
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE security.replication_guard (
    replication_in_progress INTEGER NOT NULL CHECK (replication_in_progress IN (0, 1))
);

INSERT INTO security.replication_guard (replication_in_progress) VALUES (0);

CREATE TABLE security.users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'superuser', 'dealer', 'viewer')),
    name          TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    company_id    INTEGER REFERENCES companies (id)
);

CREATE TABLE security.permissions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    permission TEXT NOT NULL UNIQUE,
    brand_id   INTEGER UNIQUE REFERENCES brands (id),
    CHECK ((permission LIKE 'brand.%.access') = (brand_id IS NOT NULL))
);

CREATE TABLE security.role_permission_rules (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    role               TEXT NOT NULL CHECK (role IN ('admin', 'superuser', 'dealer', 'viewer')),
    permission_pattern TEXT NOT NULL,
    UNIQUE (role, permission_pattern)
);

CREATE TABLE security.user_permission (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users (id),
    permission_id INTEGER NOT NULL REFERENCES permissions (id),
    UNIQUE (user_id, permission_id)
);

CREATE TRIGGER security.brand_permission_name_must_match_brand_code_on_insert
BEFORE INSERT ON permissions
WHEN NEW.brand_id IS NOT NULL
 AND NEW.permission <> 'brand.' || (SELECT code FROM brands WHERE id = NEW.brand_id) || '.access'
BEGIN
    SELECT RAISE(ABORT, 'brand permission must be named brand.<brand code>.access');
END;

CREATE TRIGGER security.brand_permission_name_must_match_brand_code_on_update
BEFORE UPDATE ON permissions
WHEN NEW.brand_id IS NOT NULL
 AND NEW.permission <> 'brand.' || (SELECT code FROM brands WHERE id = NEW.brand_id) || '.access'
BEGIN
    SELECT RAISE(ABORT, 'brand permission must be named brand.<brand code>.access');
END;

CREATE TRIGGER security.user_permission_must_be_allowed_for_role_on_insert
BEFORE INSERT ON user_permission
WHEN NOT EXISTS (
    SELECT 1
    FROM users AS granted_user
    JOIN permissions AS granted_permission ON granted_permission.id = NEW.permission_id
    JOIN role_permission_rules AS rule
      ON rule.role = granted_user.role AND granted_permission.permission LIKE rule.permission_pattern
    WHERE granted_user.id = NEW.user_id
)
BEGIN
    SELECT RAISE(ABORT, 'permission is not allowed for the role of this user');
END;

CREATE TRIGGER security.user_permission_must_be_allowed_for_role_on_update
BEFORE UPDATE ON user_permission
WHEN NOT EXISTS (
    SELECT 1
    FROM users AS granted_user
    JOIN permissions AS granted_permission ON granted_permission.id = NEW.permission_id
    JOIN role_permission_rules AS rule
      ON rule.role = granted_user.role AND granted_permission.permission LIKE rule.permission_pattern
    WHERE granted_user.id = NEW.user_id
)
BEGIN
    SELECT RAISE(ABORT, 'permission is not allowed for the role of this user');
END;

CREATE TRIGGER security.user_role_change_must_keep_granted_permissions_allowed
BEFORE UPDATE OF role ON users
WHEN EXISTS (
    SELECT 1
    FROM user_permission AS granted
    JOIN permissions AS granted_permission ON granted_permission.id = granted.permission_id
    WHERE granted.user_id = NEW.id
      AND NOT EXISTS (
          SELECT 1
          FROM role_permission_rules AS rule
          WHERE rule.role = NEW.role AND granted_permission.permission LIKE rule.permission_pattern
      )
)
BEGIN
    SELECT RAISE(ABORT, 'new role does not allow all permissions granted to this user; revoke them first');
END;

CREATE TRIGGER security.role_permission_rule_removal_must_keep_granted_permissions_allowed
BEFORE DELETE ON role_permission_rules
WHEN EXISTS (
    SELECT 1
    FROM user_permission AS granted
    JOIN users AS granted_user ON granted_user.id = granted.user_id
    JOIN permissions AS granted_permission ON granted_permission.id = granted.permission_id
    WHERE granted_user.role = OLD.role
      AND granted_permission.permission LIKE OLD.permission_pattern
      AND NOT EXISTS (
          SELECT 1
          FROM role_permission_rules AS other_rule
          WHERE other_rule.id <> OLD.id
            AND other_rule.role = granted_user.role
            AND granted_permission.permission LIKE other_rule.permission_pattern
      )
)
BEGIN
    SELECT RAISE(ABORT, 'rule still covers permissions granted to users of this role; revoke them first');
END;
