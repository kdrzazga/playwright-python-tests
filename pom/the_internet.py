from typing import Self

from playwright.sync_api import Dialog, Locator, Page


class BasePage:
    def __init__(self, page: Page, path: str) -> None:
        self.page = page
        self.path = path
        self.heading = page.locator("#content").get_by_role("heading").first

    def open(self) -> Self:
        self.page.goto(self.path)
        return self


class HomePage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/")
        self.example_links = page.locator("#content ul li a")

    def example_link(self, name: str) -> Locator:
        return self.page.get_by_role("link", name=name, exact=True)

    def go_to_example(self, name: str) -> None:
        self.example_link(name).click()


class LoginPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/login")
        self.username_input = page.locator("#username")
        self.password_input = page.locator("#password")
        self.login_button = page.locator("button[type='submit']")
        self.flash_message = page.locator("#flash")

    def login(self, username: str, password: str) -> None:
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()


class SecureAreaPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/secure")
        self.flash_message = page.locator("#flash")
        self.logout_button = page.locator("a.button[href='/logout']")

    def logout(self) -> None:
        self.logout_button.click()


class CheckboxesPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/checkboxes")
        self.checkboxes = page.locator("#checkboxes input[type='checkbox']")

    def checkbox(self, index: int) -> Locator:
        return self.checkboxes.nth(index)

    def check(self, index: int) -> None:
        self.checkbox(index).check()

    def uncheck(self, index: int) -> None:
        self.checkbox(index).uncheck()


class DropdownPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/dropdown")
        self.dropdown = page.locator("#dropdown")

    def select_option(self, label: str) -> None:
        self.dropdown.select_option(label=label)


class AddRemoveElementsPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/add_remove_elements/")
        self.add_button = page.get_by_role("button", name="Add Element")
        self.delete_buttons = page.locator("#elements button.added-manually")

    def add_elements(self, count: int) -> None:
        for _ in range(count):
            self.add_button.click()

    def remove_element(self) -> None:
        self.delete_buttons.first.click()


class JavaScriptAlertsPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/javascript_alerts")
        self.alert_button = page.get_by_role("button", name="Click for JS Alert")
        self.confirm_button = page.get_by_role("button", name="Click for JS Confirm")
        self.prompt_button = page.get_by_role("button", name="Click for JS Prompt")
        self.result = page.locator("#result")
        self.last_dialog_message = ""

    def trigger_alert(self) -> None:
        self._click_and_resolve_dialog(self.alert_button, accept=True)

    def trigger_confirm(self, accept: bool) -> None:
        self._click_and_resolve_dialog(self.confirm_button, accept=accept)

    def trigger_prompt(self, text: str) -> None:
        self._click_and_resolve_dialog(self.prompt_button, accept=True, prompt_text=text)

    def _click_and_resolve_dialog(self, button: Locator, accept: bool, prompt_text: str | None = None) -> None:
        def resolve(dialog: Dialog) -> None:
            self.last_dialog_message = dialog.message
            if accept:
                dialog.accept(prompt_text)
            else:
                dialog.dismiss()

        self.page.once("dialog", resolve)
        button.click()


class DynamicLoadingPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "/dynamic_loading/2")
        self.start_button = page.locator("#start button")
        self.loading_indicator = page.locator("#loading")
        self.finish_text = page.locator("#finish h4")

    def start(self) -> None:
        self.start_button.click()


class TheInternet:
    def __init__(self, page: Page) -> None:
        self.home = HomePage(page)
        self.login = LoginPage(page)
        self.secure_area = SecureAreaPage(page)
        self.checkboxes = CheckboxesPage(page)
        self.dropdown = DropdownPage(page)
        self.add_remove_elements = AddRemoveElementsPage(page)
        self.javascript_alerts = JavaScriptAlertsPage(page)
        self.dynamic_loading = DynamicLoadingPage(page)
