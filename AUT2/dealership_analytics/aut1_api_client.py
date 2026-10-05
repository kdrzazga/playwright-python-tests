import requests


class Aut1UnavailableError(Exception):
    pass


class Aut1ApiClient:
    def __init__(self, base_url, username, password, request_timeout_seconds=40):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.request_timeout_seconds = request_timeout_seconds
        self._http_session = requests.Session()
        self._logged_in = False

    def fetch_all_records_of_table(self, database_name, table_name):
        first_page = self._fetch_table_page(database_name, table_name, 1)
        records = list(first_page["records"])
        for page_number in range(2, first_page["total_page_count"] + 1):
            records.extend(self._fetch_table_page(database_name, table_name, page_number)["records"])
        return records

    def _fetch_table_page(self, database_name, table_name, page_number):
        table_page_url = f"{self.base_url}/api/database/tables/{database_name}/{table_name}?page={page_number}"
        if not self._logged_in:
            self._log_in()
        response = self._send("GET", table_page_url)
        if response.status_code == 401:
            self._log_in()
            response = self._send("GET", table_page_url)
        if response.status_code != 200:
            raise Aut1UnavailableError(
                f"AUT1 answered HTTP {response.status_code} for {database_name}.{table_name}: {self._read_error(response)}"
            )
        return response.json()

    def _log_in(self):
        response = self._send("POST", f"{self.base_url}/api/login", json={"username": self.username, "password": self.password})
        if response.status_code != 200:
            self._logged_in = False
            raise Aut1UnavailableError(f"AUT1 login as '{self.username}' failed: {self._read_error(response)}")
        if not response.json().get("can_view_whole_database"):
            raise Aut1UnavailableError(f"AUT1 user '{self.username}' lacks the view_db_tables permission")
        self._logged_in = True

    def _send(self, method, url, **request_options):
        try:
            return self._http_session.request(method, url, timeout=self.request_timeout_seconds, **request_options)
        except requests.RequestException as error:
            self._logged_in = False
            raise Aut1UnavailableError(f"AUT1 is not reachable at {self.base_url}: {type(error).__name__}") from error

    @staticmethod
    def _read_error(response):
        try:
            return response.json().get("error", response.reason)
        except ValueError:
            return response.reason
