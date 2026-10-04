import { ApiClient, PageNavigator } from "./api_client.js";
import { LogoutButton } from "./logout_button.js";

class HomePage {
    constructor(apiClient, pageNavigator) {
        this.apiClient = apiClient;
        this.pageNavigator = pageNavigator;
        this.welcomeMessage = document.querySelector("[data-testid='welcome-message']");
        this.showWholeDatabaseButton = document.querySelector("[data-testid='show-whole-db-button']");
    }

    async renderForLoggedInUser() {
        try {
            const loggedInUser = await this.apiClient.fetchLoggedInUser();
            this.welcomeMessage.textContent = `Welcome, ${loggedInUser.username}`;
            this.#showWholeDatabaseButtonWhenUserIsAllowed(loggedInUser);
        } catch {
            this.pageNavigator.goToLoginPage();
        }
    }

    #showWholeDatabaseButtonWhenUserIsAllowed(loggedInUser) {
        if (!loggedInUser.can_view_whole_database) {
            return;
        }
        this.showWholeDatabaseButton.hidden = false;
        this.showWholeDatabaseButton.addEventListener("click", () => this.pageNavigator.goToDatabasePage());
    }
}

const apiClient = new ApiClient();
const pageNavigator = new PageNavigator();
new LogoutButton(apiClient, pageNavigator).startListeningForClicks();
new HomePage(apiClient, pageNavigator).renderForLoggedInUser();
