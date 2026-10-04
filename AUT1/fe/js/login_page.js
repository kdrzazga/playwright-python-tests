import { ApiClient, PageNavigator } from "./api_client.js";

class LoginPage {
    constructor(apiClient, pageNavigator) {
        this.apiClient = apiClient;
        this.pageNavigator = pageNavigator;
        this.loginForm = document.querySelector("[data-testid='login-form']");
        this.usernameInput = document.querySelector("[data-testid='username-input']");
        this.passwordInput = document.querySelector("[data-testid='password-input']");
        this.loginButton = document.querySelector("[data-testid='login-button']");
        this.errorMessage = document.querySelector("[data-testid='login-error-message']");
    }

    startListeningForLoginSubmission() {
        this.loginForm.addEventListener("submit", (submitEvent) => {
            submitEvent.preventDefault();
            this.#logInWithEnteredCredentials();
        });
    }

    async #logInWithEnteredCredentials() {
        this.#hideErrorMessage();
        this.loginButton.disabled = true;
        try {
            await this.apiClient.logIn(this.usernameInput.value.trim(), this.passwordInput.value);
            this.pageNavigator.goToHomePage();
        } catch (error) {
            this.#showErrorMessage(error.message);
            this.loginButton.disabled = false;
        }
    }

    #showErrorMessage(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.hidden = false;
    }

    #hideErrorMessage() {
        this.errorMessage.textContent = "";
        this.errorMessage.hidden = true;
    }
}

new LoginPage(new ApiClient(), new PageNavigator()).startListeningForLoginSubmission();
