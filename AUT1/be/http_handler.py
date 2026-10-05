import json
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from authentication import FrontEndAccessDeniedError, InvalidCredentialsError
from database_errors import PageOutOfRangeError, TableNotFoundError


class MalformedRequestBodyError(ValueError):
    pass


class CarDealerHttpServer(ThreadingHTTPServer):
    def __init__(self, server_address, application):
        super().__init__(server_address, CarDealerRequestHandler)
        self.application = application


class CarDealerRequestHandler(BaseHTTPRequestHandler):
    @property
    def application(self):
        return self.server.application

    def do_GET(self):
        request_path = self._read_request_path()
        single_table_api_path_prefix = self.application.single_table_api_path_prefix
        api_routes = {
            "/": self._redirect_to_login_page,
            "/api/session": self._respond_with_logged_in_user,
            "/api/database/tables": self._respond_with_first_page_of_all_tables,
        }
        if request_path in api_routes:
            api_routes[request_path]()
        elif request_path.startswith(single_table_api_path_prefix):
            self._respond_with_requested_page_of_single_table(request_path.removeprefix(single_table_api_path_prefix))
        elif self.application.is_protected_page(request_path):
            self._serve_protected_page_or_redirect_to_login(request_path)
        else:
            self._serve_public_front_end_file(request_path)

    def do_POST(self):
        api_routes = {
            "/api/login": self._log_in_and_set_session_cookie,
            "/api/logout": self._log_out_and_clear_session_cookie,
        }
        route = api_routes.get(self._read_request_path())
        if route is None:
            self._respond_with_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            route()
        except MalformedRequestBodyError as error:
            self._respond_with_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def _log_in_and_set_session_cookie(self):
        credentials = self._read_json_object_from_request_body()
        try:
            session_token = self.application.authentication_service.log_in_to_front_end_and_open_session(
                str(credentials.get("username", "")),
                str(credentials.get("password", "")),
            )
        except InvalidCredentialsError as error:
            self._respond_with_json(HTTPStatus.UNAUTHORIZED, {"error": str(error)})
        except FrontEndAccessDeniedError as error:
            self._respond_with_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        else:
            user_session = self.application.authentication_service.find_session_by_session_token(session_token)
            self._respond_with_json(
                HTTPStatus.OK,
                user_session.describe_with_login_time_formatted_as(self.application.login_time_format),
                extra_headers={"Set-Cookie": self._build_session_cookie_header(session_token)},
            )

    def _log_out_and_clear_session_cookie(self):
        self.application.authentication_service.log_out_session(self._read_session_token_from_cookie())
        self._respond_with_json(
            HTTPStatus.OK,
            {"logged_out": True},
            extra_headers={"Set-Cookie": self._build_expired_session_cookie_header()},
        )

    def _respond_with_logged_in_user(self):
        user_session = self.application.authentication_service.find_session_by_session_token(
            self._read_session_token_from_cookie()
        )
        if user_session is None:
            self._respond_with_json(HTTPStatus.UNAUTHORIZED, {"error": "Not logged in"})
        else:
            self._respond_with_json(
                HTTPStatus.OK,
                user_session.describe_with_login_time_formatted_as(self.application.login_time_format),
            )

    def _respond_with_first_page_of_all_tables(self):
        if self._respond_with_error_unless_logged_in_user_can_view_whole_database():
            return
        self._respond_with_json(HTTPStatus.OK, self.application.describe_first_page_of_all_tables_for_display())

    def _respond_with_requested_page_of_single_table(self, database_and_table_path):
        if self._respond_with_error_unless_logged_in_user_can_view_whole_database():
            return
        database_name, _, table_name = database_and_table_path.partition("/")
        try:
            table_page = self.application.describe_table_page_for_display(
                database_name, table_name, self._read_page_number_from_query_string()
            )
        except TableNotFoundError as error:
            self._respond_with_json(HTTPStatus.NOT_FOUND, {"error": str(error)})
        except PageOutOfRangeError as error:
            self._respond_with_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        else:
            self._respond_with_json(HTTPStatus.OK, table_page)

    def _respond_with_error_unless_logged_in_user_can_view_whole_database(self):
        logged_in_user = self._find_logged_in_user()
        if logged_in_user is None:
            self._respond_with_json(HTTPStatus.UNAUTHORIZED, {"error": "Not logged in"})
            return True
        if not logged_in_user.can_view_whole_database:
            self._respond_with_json(HTTPStatus.FORBIDDEN, {"error": "Only admin can view the whole database"})
            return True
        return False

    def _read_page_number_from_query_string(self):
        requested_page = parse_qs(urlsplit(self.path).query).get("page", ["1"])[0]
        try:
            return int(requested_page)
        except ValueError as error:
            raise PageOutOfRangeError(f"Page '{requested_page}' is not a whole number") from error

    def _serve_protected_page_or_redirect_to_login(self, request_path):
        if self.application.user_is_allowed_to_open_page(self._find_logged_in_user(), request_path):
            self._serve_public_front_end_file(request_path)
        else:
            self._redirect_to_login_page()

    def _serve_public_front_end_file(self, request_path):
        front_end_file = self.application.find_front_end_file_for_request_path(request_path)
        if front_end_file is None:
            self._respond_with_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        self._send_response_body(
            HTTPStatus.OK,
            front_end_file.read_bytes(),
            self.application.content_type_for_file(front_end_file),
        )

    def _redirect_to_login_page(self):
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", self.application.login_page_path)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _find_logged_in_user(self):
        return self.application.authentication_service.find_logged_in_user_by_session_token(
            self._read_session_token_from_cookie()
        )

    def _read_session_token_from_cookie(self):
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        session_cookie = cookies.get(self.application.session_cookie_name)
        return session_cookie.value if session_cookie else None

    def _build_session_cookie_header(self, session_token):
        return f"{self.application.session_cookie_name}={session_token}; Path=/; HttpOnly; SameSite=Strict"

    def _build_expired_session_cookie_header(self):
        return f"{self.application.session_cookie_name}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"

    def _read_request_path(self):
        return urlsplit(self.path).path

    def _read_json_object_from_request_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)
        try:
            parsed_body = json.loads(raw_body or b"{}")
        except json.JSONDecodeError as error:
            raise MalformedRequestBodyError("Request body is not valid JSON") from error
        if not isinstance(parsed_body, dict):
            raise MalformedRequestBodyError("Request body must be a JSON object")
        return parsed_body

    def _respond_with_json(self, status, payload, extra_headers=None):
        self._send_response_body(
            status,
            json.dumps(payload).encode(),
            "application/json; charset=utf-8",
            extra_headers,
        )

    def _send_response_body(self, status, body, content_type, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for header_name, header_value in (extra_headers or {}).items():
            self.send_header(header_name, header_value)
        self.end_headers()
        self.wfile.write(body)
