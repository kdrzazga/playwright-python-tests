from tests.credentials import Credentials


class Aut1SeededUsers:
    def __init__(
        self,
        dealer_username: str = "dealer_tesla_vw",
        dealer_accessible_brand_names: tuple[str, ...] = ("Tesla", "Volkswagen"),
        username_without_frontend_access: str = "obsolete_vw",
    ) -> None:
        self.dealer = self._credentials_with_password_equal_to_username(dealer_username)
        self.dealer_accessible_brand_names = dealer_accessible_brand_names
        self.user_without_frontend_access = self._credentials_with_password_equal_to_username(username_without_frontend_access)

    def _credentials_with_password_equal_to_username(self, username: str) -> Credentials:
        return Credentials(username=username, password=username)
