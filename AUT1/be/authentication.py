import hmac
import secrets
from dataclasses import dataclass
from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    SUPERUSER = "superuser"
    BRAND_USER = "brand_user"
    VIEWER = "viewer"


@dataclass(frozen=True)
class User:
    username: str
    password: str
    role: UserRole
    assigned_brand: str | None = None

    @property
    def can_access_front_end(self):
        return self.role is UserRole.ADMIN

    @property
    def can_view_whole_database(self):
        return self.role is UserRole.ADMIN

    def describe_without_password(self):
        return {
            "username": self.username,
            "role": self.role,
            "assigned_brand": self.assigned_brand,
            "can_view_whole_database": self.can_view_whole_database,
        }


class InvalidCredentialsError(Exception):
    pass


class FrontEndAccessDeniedError(Exception):
    pass


class UserRepository:
    def __init__(self, users):
        self._users_by_username = {user.username: user for user in users}

    @classmethod
    def with_default_application_users(cls):
        return cls(
            (
                User("admin", "admin", UserRole.ADMIN),
                User("superuser", "superuser", UserRole.SUPERUSER),
                User("user_vw", "user_vw", UserRole.BRAND_USER, assigned_brand="Volkswagen"),
                User("user_tesla", "user_tesla", UserRole.BRAND_USER, assigned_brand="Tesla"),
                User("viewer", "viewer", UserRole.VIEWER),
            )
        )

    def find_user_by_username(self, username):
        return self._users_by_username.get(username)


class SessionStore:
    def __init__(self):
        self._users_by_session_token = {}

    def open_session_for_user(self, user):
        session_token = secrets.token_urlsafe(32)
        self._users_by_session_token[session_token] = user
        return session_token

    def find_user_by_session_token(self, session_token):
        return self._users_by_session_token.get(session_token)

    def close_session(self, session_token):
        self._users_by_session_token.pop(session_token, None)


class AuthenticationService:
    def __init__(self, user_repository, session_store):
        self.user_repository = user_repository
        self.session_store = session_store

    def log_in_to_front_end_and_open_session(self, username, password):
        user = self._find_user_matching_credentials(username, password)
        if not user.can_access_front_end:
            raise FrontEndAccessDeniedError(f"User '{username}' is not allowed to access the front-end")
        return self.session_store.open_session_for_user(user)

    def find_logged_in_user_by_session_token(self, session_token):
        if session_token is None:
            return None
        return self.session_store.find_user_by_session_token(session_token)

    def log_out_session(self, session_token):
        if session_token is not None:
            self.session_store.close_session(session_token)

    def _find_user_matching_credentials(self, username, password):
        user = self.user_repository.find_user_by_username(username)
        if user is None or not self._passwords_match(user.password, password):
            raise InvalidCredentialsError("Invalid username or password")
        return user

    @staticmethod
    def _passwords_match(expected_password, provided_password):
        return hmac.compare_digest(expected_password.encode(), provided_password.encode())
