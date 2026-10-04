export class LogoutButton {
    constructor(apiClient, pageNavigator) {
        this.apiClient = apiClient;
        this.pageNavigator = pageNavigator;
        this.button = document.querySelector("[data-testid='logout-button']");
    }

    startListeningForClicks() {
        this.button.addEventListener("click", () => this.#logOutAndGoToLoginPage());
    }

    async #logOutAndGoToLoginPage() {
        try {
            await this.apiClient.logOut();
        } finally {
            this.pageNavigator.goToLoginPage();
        }
    }
}
