import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime

from records import PermissionName, UserRole


class Pbkdf2PasswordHasher:
    def __init__(self, iterations=100_000, salt_length_bytes=16, hash_algorithm="sha256"):
        self.iterations = iterations
        self.salt_length_bytes = salt_length_bytes
        self.hash_algorithm = hash_algorithm

    def hash_password(self, password, salt_hex=None):
        salt_hex = salt_hex or secrets.token_hex(self.salt_length_bytes)
        derived_key_hex = self._derive_key_hex(password, salt_hex, self.iterations, self.hash_algorithm)
        return f"pbkdf2_{self.hash_algorithm}${self.iterations}${salt_hex}${derived_key_hex}"

    def password_matches_hash(self, password, password_hash):
        scheme, iterations, salt_hex, expected_key_hex = password_hash.split("$")
        hash_algorithm = scheme.removeprefix("pbkdf2_")
        actual_key_hex = self._derive_key_hex(password, salt_hex, int(iterations), hash_algorithm)
        return hmac.compare_digest(actual_key_hex, expected_key_hex)

    @staticmethod
    def _derive_key_hex(password, salt_hex, iterations, hash_algorithm):
        return hashlib.pbkdf2_hmac(hash_algorithm, password.encode(), bytes.fromhex(salt_hex), iterations).hex()


@dataclass(frozen=True)
class User:
    id: int
    username: str
    password_hash: str
    role: UserRole
    name: str
    last_name: str
    company_id: int | None
    permissions: frozenset
    accessible_brand_names: frozenset

    @property
    def can_view_whole_database(self):
        return self.has_permission(PermissionName.VIEW_DB_TABLES)

    def has_permission(self, permission_name):
        return permission_name in self.permissions

    def has_access_to_brand(self, brand_name):
        return brand_name in self.accessible_brand_names

    def describe_without_password(self):
        return {
            "username": self.username,
            "role": self.role,
            "name": self.name,
            "last_name": self.last_name,
            "company_id": self.company_id,
            "permissions": sorted(self.permissions),
            "accessible_brands": sorted(self.accessible_brand_names),
            "can_view_whole_database": self.can_view_whole_database,
        }


class InvalidCredentialsError(Exception):
    pass


class FrontEndAccessDeniedError(Exception):
    pass


class DatabaseUserRepository:
    def __init__(self, database):
        self.database = database

    def list_all_users(self):
        username_rows = self.database.connection.fetch_all_rows(
            f"SELECT username FROM {self.database.users.qualified_table_name} ORDER BY id"
        )
        return [self.find_user_by_username(username_row["username"]) for username_row in username_rows]

    def find_user_by_username(self, username):
        user_row = self.database.connection.fetch_single_row(
            f"SELECT * FROM {self.database.users.qualified_table_name} WHERE username = ?", (username,)
        )
        if user_row is None:
            return None
        user_account = self.database.users.map_row_to_record(user_row)
        return User(
            id=user_account.id,
            username=user_account.username,
            password_hash=user_account.password_hash,
            role=user_account.role,
            name=user_account.name,
            last_name=user_account.last_name,
            company_id=user_account.company_id,
            permissions=self._load_permission_names_of_user(user_account.id),
            accessible_brand_names=self._load_accessible_brand_names_of_user(user_account.id),
        )

    def _load_permission_names_of_user(self, user_id):
        permission_rows = self.database.connection.fetch_all_rows(
            f"SELECT permission_definition.permission "
            f"FROM {self.database.user_permissions.qualified_table_name} AS granted_permission "
            f"JOIN {self.database.permissions.qualified_table_name} AS permission_definition "
            f"ON permission_definition.id = granted_permission.permission_id "
            f"WHERE granted_permission.user_id = ?",
            (user_id,),
        )
        return frozenset(permission_row["permission"] for permission_row in permission_rows)

    def _load_accessible_brand_names_of_user(self, user_id):
        brand_rows = self.database.connection.fetch_all_rows(
            f"SELECT accessible_brand.name "
            f"FROM {self.database.user_permissions.qualified_table_name} AS granted_permission "
            f"JOIN {self.database.permissions.qualified_table_name} AS permission_definition "
            f"ON permission_definition.id = granted_permission.permission_id "
            f"JOIN {self.database.security_brands.qualified_table_name} AS accessible_brand "
            f"ON accessible_brand.id = permission_definition.brand_id "
            f"WHERE granted_permission.user_id = ?",
            (user_id,),
        )
        return frozenset(brand_row["name"] for brand_row in brand_rows)


@dataclass(frozen=True)
class UserSession:
    user: User
    logged_in_at: datetime

    def describe_with_login_time_formatted_as(self, login_time_format):
        return {
            **self.user.describe_without_password(),
            "logged_in_at": self.logged_in_at.strftime(login_time_format),
        }


class SessionStore:
    def __init__(self, current_time_provider=datetime.now):
        self.current_time_provider = current_time_provider
        self._sessions_by_session_token = {}

    def open_session_for_user(self, user):
        session_token = secrets.token_urlsafe(32)
        self._sessions_by_session_token[session_token] = UserSession(user, self.current_time_provider())
        return session_token

    def find_session_by_session_token(self, session_token):
        return self._sessions_by_session_token.get(session_token)

    def close_session(self, session_token):
        self._sessions_by_session_token.pop(session_token, None)


class AuthenticationService:
    def __init__(
        self,
        user_repository,
        session_store,
        password_hasher,
        front_end_access_permission=PermissionName.FRONTEND_ACCESS,
    ):
        self.user_repository = user_repository
        self.session_store = session_store
        self.password_hasher = password_hasher
        self.front_end_access_permission = front_end_access_permission

    def log_in_to_front_end_and_open_session(self, username, password):
        user = self._find_user_matching_credentials(username, password)
        if not self.user_may_use_front_end(user):
            raise FrontEndAccessDeniedError(f"User '{username}' is not allowed to access the front-end")
        return self.session_store.open_session_for_user(user)

    def user_may_use_front_end(self, user):
        return user.has_permission(self.front_end_access_permission)

    def find_session_by_session_token(self, session_token):
        if session_token is None:
            return None
        return self.session_store.find_session_by_session_token(session_token)

    def find_logged_in_user_by_session_token(self, session_token):
        user_session = self.find_session_by_session_token(session_token)
        return None if user_session is None else user_session.user

    def log_out_session(self, session_token):
        if session_token is not None:
            self.session_store.close_session(session_token)

    def _find_user_matching_credentials(self, username, password):
        user = self.user_repository.find_user_by_username(username)
        if user is None or not self.password_hasher.password_matches_hash(password, user.password_hash):
            raise InvalidCredentialsError("Invalid username or password")
        return user
