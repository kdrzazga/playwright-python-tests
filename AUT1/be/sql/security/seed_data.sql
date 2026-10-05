INSERT INTO security.users (username, password_hash, role, name, last_name, company_id) VALUES
    ('admin', 'pbkdf2_sha256$100000$eb39270be01d8e8a82710e01ec0dfba2$94164bff5fb7c9cd090f7e164dbe66582736276222fafa3d455a904041f66c45', 'admin', 'Alice', 'Morgan', NULL),
    ('superuser', 'pbkdf2_sha256$100000$07b02dd8dae7439f78ca13d27ab7ce20$8c7f2896cc5683452b42153630344c2e2c2e9cd85ee037fc995c5f5a663bb315', 'superuser', 'Bruno', 'Keller', NULL),
    ('user_vw', 'pbkdf2_sha256$100000$62eca63b388cf17d6157c337c95eee63$e4ad6c28054e7941afc327e35d5c038281153d50a29527616c1225d5a5d4e441', 'viewer', 'Clara', 'Schmidt', NULL),
    ('dealer_tesla_vw', 'pbkdf2_sha256$100000$8b355568d7e796f36d916e9a843c87aa$cd09b73e212da03f0804e6abc18009c797610437040ac4bb0ba7b88e84fc7527', 'dealer', 'Daniel', 'Price', NULL),
    ('viewer', 'pbkdf2_sha256$100000$264389c3992b93ca93076b633a371e10$eaa6b5346199a425bce2c11cef3fa699eb47df376a2db7a9b74d3ae00a29d701', 'viewer', 'Eva', 'Lindgren', NULL),
    ('obsolete_vw', 'pbkdf2_sha256$100000$bcc49d84a8e6c582d0872c0287ad1ec6$18d069814477c4dbc0ff2921e16e65fdda3459af479a3d90e4ec26ce7d6c9d4b', 'viewer', 'Oskar', 'Brandt', NULL);

INSERT INTO security.permissions (permission, brand_id) VALUES
    ('view_db_tables', NULL),
    ('vehicle.view', NULL),
    ('vehicle.add', NULL),
    ('vehicle.modify', NULL),
    ('vehicle.remove', NULL),
    ('rental.view', NULL),
    ('rental.add', NULL),
    ('rental.modify', NULL),
    ('rental.remove', NULL),
    ('sell.view', NULL),
    ('sell.add', NULL),
    ('sell.modify', NULL),
    ('sell.remove', NULL),
    ('loan.view', NULL),
    ('loan.add', NULL),
    ('loan.modify', NULL),
    ('loan.remove', NULL),
    ('brand.vw.access', (SELECT id FROM security.brands WHERE code = 'vw')),
    ('brand.toyota.access', (SELECT id FROM security.brands WHERE code = 'toyota')),
    ('brand.mercedes.access', (SELECT id FROM security.brands WHERE code = 'mercedes')),
    ('brand.tesla.access', (SELECT id FROM security.brands WHERE code = 'tesla')),
    ('brand.skoda.access', (SELECT id FROM security.brands WHERE code = 'skoda')),
    ('brand.bmw.access', (SELECT id FROM security.brands WHERE code = 'bmw'));

INSERT INTO security.permissions (permission, brand_id) VALUES
    ('frontend.access', NULL);

INSERT INTO security.role_permission_rules (role, permission_pattern) VALUES
    ('admin', 'view_db_tables'),
    ('admin', 'vehicle.view'),
    ('admin', 'vehicle.modify'),
    ('admin', 'vehicle.remove'),
    ('admin', 'rental.%'),
    ('admin', 'sell.%'),
    ('admin', 'loan.%'),
    ('admin', 'brand.%.access'),
    ('superuser', 'vehicle.%'),
    ('superuser', 'rental.%'),
    ('superuser', 'sell.%'),
    ('superuser', 'loan.%'),
    ('superuser', 'brand.%.access'),
    ('dealer', 'vehicle.%'),
    ('dealer', 'rental.%'),
    ('dealer', 'sell.%'),
    ('dealer', 'loan.view'),
    ('dealer', 'brand.%.access'),
    ('viewer', '%.view'),
    ('viewer', 'brand.%.access'),
    ('admin', 'frontend.access'),
    ('superuser', 'frontend.access'),
    ('dealer', 'frontend.access'),
    ('viewer', 'frontend.access');

INSERT INTO security.user_permission (user_id, permission_id)
SELECT granted_user.id, granted_permission.id
FROM security.users AS granted_user, security.permissions AS granted_permission
WHERE granted_user.username = 'admin'
  AND (granted_permission.permission <> 'vehicle.add');

INSERT INTO security.user_permission (user_id, permission_id)
SELECT granted_user.id, granted_permission.id
FROM security.users AS granted_user, security.permissions AS granted_permission
WHERE granted_user.username = 'superuser'
  AND (granted_permission.permission <> 'view_db_tables');

INSERT INTO security.user_permission (user_id, permission_id)
SELECT granted_user.id, granted_permission.id
FROM security.users AS granted_user, security.permissions AS granted_permission
WHERE granted_user.username = 'viewer'
  AND (granted_permission.permission LIKE '%.view' OR granted_permission.permission LIKE 'brand.%.access'
       OR granted_permission.permission = 'frontend.access');

INSERT INTO security.user_permission (user_id, permission_id)
SELECT granted_user.id, granted_permission.id
FROM security.users AS granted_user, security.permissions AS granted_permission
WHERE granted_user.username = 'user_vw'
  AND (granted_permission.permission LIKE '%.view'
       OR granted_permission.permission IN ('brand.vw.access', 'frontend.access'));

INSERT INTO security.user_permission (user_id, permission_id)
SELECT granted_user.id, granted_permission.id
FROM security.users AS granted_user, security.permissions AS granted_permission
WHERE granted_user.username = 'dealer_tesla_vw'
  AND (granted_permission.permission LIKE '%.view'
       OR granted_permission.permission IN ('vehicle.add', 'vehicle.remove', 'brand.tesla.access', 'brand.vw.access',
                                            'frontend.access'));

INSERT INTO security.user_permission (user_id, permission_id)
SELECT granted_user.id, granted_permission.id
FROM security.users AS granted_user, security.permissions AS granted_permission
WHERE granted_user.username = 'obsolete_vw'
  AND granted_permission.permission IN ('vehicle.view', 'brand.vw.access');
