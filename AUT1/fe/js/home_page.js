import { ApiClient, PageNavigator } from "./api_client.js";
import { LogoutButton } from "./logout_button.js";
import { SessionFooter } from "./session_footer.js";

class HomePage {
    constructor(apiClient, pageNavigator, sessionFooter) {
        this.apiClient = apiClient;
        this.pageNavigator = pageNavigator;
        this.sessionFooter = sessionFooter;
        this.welcomeMessage = document.querySelector("[data-testid='welcome-message']");
        this.showWholeDatabaseButton = document.querySelector("[data-testid='show-whole-db-button']");
        this.vehiclesButton = document.querySelector("[data-testid='vehicles-button']");
    }

    async renderForLoggedInUser() {
        try {
            const loggedInUser = await this.apiClient.fetchLoggedInUser();
            this.welcomeMessage.textContent = `Welcome, ${loggedInUser.username}`;
            this.#showWholeDatabaseButtonWhenUserIsAllowed(loggedInUser);
            this.#showVehiclesButtonWhenUserMayViewVehicles(loggedInUser);
            this.sessionFooter.renderForLoggedInUser(loggedInUser);
        } catch {
            this.pageNavigator.goToLoginPage();
        }
    }

    #showVehiclesButtonWhenUserMayViewVehicles(loggedInUser) {
        if (!loggedInUser.permissions.includes("vehicle.view")) {
            return;
        }
        this.vehiclesButton.hidden = false;
        this.vehiclesButton.addEventListener("click", () => this.pageNavigator.goToVehiclesPage());
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
new HomePage(apiClient, pageNavigator, new SessionFooter()).renderForLoggedInUser();
