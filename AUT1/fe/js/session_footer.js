export class SessionFooter {
    constructor() {
        this.footer = document.querySelector("[data-testid='session-footer']");
        this.usernameElement = document.querySelector("[data-testid='footer-username']");
        this.loginTimeElement = document.querySelector("[data-testid='footer-login-time']");
    }

    renderForLoggedInUser(loggedInUser) {
        this.usernameElement.textContent = loggedInUser.username;
        this.loginTimeElement.textContent = loggedInUser.logged_in_at;
        this.footer.hidden = false;
    }
}
