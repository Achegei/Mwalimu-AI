const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const loginButton = document.getElementById("login-button");


function showLoginError(message) {
    if (!loginError) {
        return;
    }

    loginError.textContent = message;
    loginError.hidden = false;
}


function clearLoginError() {
    if (!loginError) {
        return;
    }

    loginError.textContent = "";
    loginError.hidden = true;
}


function setLoginLoading(isLoading) {
    if (!loginButton) {
        return;
    }

    loginButton.disabled = isLoading;
    loginButton.textContent = isLoading
        ? "Signing in..."
        : "Sign in";
}


function storeAuthentication(accessToken, user) {
    localStorage.setItem(
        "mwalimu_access_token",
        accessToken,
    );

    localStorage.setItem(
        "mwalimu_user",
        JSON.stringify(user),
    );
}


function redirectForRole(role) {
    if (role === "student") {
        window.location.href = "/student/dashboard";
        return;
    }

    if (role === "teacher") {
        window.location.href = "/teacher/dashboard";
        return;
    }

    if (role === "admin") {
        window.location.href = "/admin/dashboard";
        return;
    }

    localStorage.removeItem("mwalimu_access_token");
    localStorage.removeItem("mwalimu_user");

    showLoginError(
        "Your account does not have access to this application.",
    );
}


async function verifyCurrentUser(accessToken) {
    const response = await fetch(
        "/auth/me",
        {
            method: "GET",
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
        },
    );

    if (!response.ok) {
        throw new Error(
            "Unable to verify your account.",
        );
    }

    return response.json();
}


async function handleLogin(event) {
    event.preventDefault();

    clearLoginError();
    setLoginLoading(true);

    const loginId = document
        .getElementById("login-id")
        .value
        .trim();

    const password = document
        .getElementById("password")
        .value;

    if (!loginId || !password) {
        showLoginError(
            "Enter your login ID and password.",
        );

        setLoginLoading(false);
        return;
    }

    try {
        const response = await fetch(
            "/auth/login",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    login_id: loginId,
                    password: password,
                }),
            },
        );

        const data = await response.json();

        if (!response.ok) {
            let message = "Unable to sign in.";

            if (
                data &&
                typeof data.detail === "string"
            ) {
                message = data.detail;
            }

            showLoginError(message);
            return;
        }

        const accessToken = data.access_token;

        if (!accessToken) {
            throw new Error(
                "Authentication token was not returned.",
            );
        }

        const currentUser = await verifyCurrentUser(
            accessToken,
        );

        storeAuthentication(
            accessToken,
            currentUser,
        );

        redirectForRole(
            currentUser.role,
        );

    } catch (error) {
        console.error(
            "Login error:",
            error,
        );

        showLoginError(
            "We could not sign you in. Please try again.",
        );

    } finally {
        setLoginLoading(false);
    }
}


if (loginForm) {
    loginForm.addEventListener(
        "submit",
        handleLogin,
    );
}
