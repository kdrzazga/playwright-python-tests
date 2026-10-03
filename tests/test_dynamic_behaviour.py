from playwright.sync_api import expect

from pom import TheInternet


class TestJavaScriptAlerts:
    def test_accept_alert(self, the_internet: TheInternet) -> None:
        alerts = the_internet.javascript_alerts.open()

        alerts.trigger_alert()

        assert alerts.last_dialog_message == "I am a JS Alert"
        expect(alerts.result).to_have_text("You successfully clicked an alert")

    def test_accept_confirm(self, the_internet: TheInternet) -> None:
        alerts = the_internet.javascript_alerts.open()

        alerts.trigger_confirm(accept=True)

        expect(alerts.result).to_have_text("You clicked: Ok")

    def test_dismiss_confirm(self, the_internet: TheInternet) -> None:
        alerts = the_internet.javascript_alerts.open()

        alerts.trigger_confirm(accept=False)

        expect(alerts.result).to_have_text("You clicked: Cancel")

    def test_answer_prompt(self, the_internet: TheInternet) -> None:
        alerts = the_internet.javascript_alerts.open()

        alerts.trigger_prompt("Playwright")

        expect(alerts.result).to_have_text("You entered: Playwright")


class TestDynamicLoading:
    def test_element_rendered_after_loading(self, the_internet: TheInternet) -> None:
        dynamic_loading = the_internet.dynamic_loading.open()

        dynamic_loading.start()

        expect(dynamic_loading.loading_indicator).to_be_hidden()
        expect(dynamic_loading.finish_text).to_have_text("Hello World!")
