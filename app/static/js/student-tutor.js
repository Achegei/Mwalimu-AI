const accessToken = localStorage.getItem("mwalimu_access_token");
const diagnosticAttemptId =
    window.MWALIMU_DIAGNOSTIC_ATTEMPT_ID;

const studentName = document.getElementById("student-name");
const logoutButton = document.getElementById("logout-button");

const tutorError = document.getElementById("tutor-error");
const tutorLoading = document.getElementById("tutor-loading");
const tutorMain = document.getElementById("tutor-main");

const tutorTopicTitle = document.getElementById(
    "tutor-topic-title",
);

const tutorConversation = document.getElementById(
    "tutor-conversation",
);

const tutorForm = document.getElementById("tutor-form");
const tutorMessage = document.getElementById("tutor-message");

const sendMessageButton = document.getElementById(
    "send-message-button",
);

const continuePracticeButton = document.getElementById(
    "continue-practice-button",
);


function redirectToLogin() {
    localStorage.removeItem("mwalimu_access_token");
    localStorage.removeItem("mwalimu_user");

    window.location.href = "/";
}


function showError(message) {
    if (!tutorError) {
        return;
    }

    tutorError.textContent = message;
    tutorError.hidden = false;
}


function hideError() {
    if (!tutorError) {
        return;
    }

    tutorError.textContent = "";
    tutorError.hidden = true;
}


function setLoading(isLoading) {
    if (tutorLoading) {
        tutorLoading.hidden = !isLoading;
    }

    if (tutorMain) {
        tutorMain.hidden = isLoading;
    }
}


async function apiRequest(
    url,
    options = {},
) {
    const headers = {
        Authorization: `Bearer ${accessToken}`,
        ...(options.headers || {}),
    };

    const response = await fetch(
        url,
        {
            ...options,
            headers,
        },
    );

    if (response.status === 401) {
        redirectToLogin();
        return null;
    }

    if (response.status === 403) {
        throw new Error(
            "You do not have permission to access this resource.",
        );
    }

    if (!response.ok) {
        let message = "Unable to complete the request.";

        try {
            const data = await response.json();

            if (
                data
                && typeof data.detail === "string"
            ) {
                message = data.detail;
            }
        } catch (error) {
            console.error(
                "Unable to parse API error:",
                error,
            );
        }

        throw new Error(message);
    }

    return response.json();
}


async function loadCurrentUser() {
    const user = await apiRequest("/auth/me");

    if (!user) {
        return null;
    }

    if (user.role !== "student") {
        redirectToLogin();
        return null;
    }

    localStorage.setItem(
        "mwalimu_user",
        JSON.stringify(user),
    );

    if (studentName) {
        studentName.textContent = user.full_name;
    }

    return user;
}


function appendMessage(role, message) {
    if (!tutorConversation) {
        return;
    }

    const wrapper = document.createElement("div");
    wrapper.className = (
        role === "student"
            ? "card tutor-message tutor-message--student"
            : "card tutor-message tutor-message--assistant"
    );

    const label = document.createElement("p");
    label.className = "text-muted mb-1";
    label.textContent = (
        role === "student"
            ? "You"
            : "Mwalimu AI"
    );

    const content = document.createElement("p");
    content.className = "mb-0";
    content.textContent = message;

    wrapper.appendChild(label);
    wrapper.appendChild(content);

    tutorConversation.appendChild(wrapper);
}


async function startTutorSession() {
    const data = await apiRequest(
        `/student/diagnostic/${diagnosticAttemptId}/tutor/start`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        },
    );

    if (!data) {
        return null;
    }

    if (tutorTopicTitle) {
        tutorTopicTitle.textContent =
            "AI Tutor";
    }

    appendMessage(
        "assistant",
        data.message,
    );

    return data;
}


async function initializeTutor() {
    if (!accessToken) {
        redirectToLogin();
        return;
    }

    if (!diagnosticAttemptId) {
        setLoading(false);

        showError(
            "The diagnostic attempt could not be identified.",
        );

        return;
    }

    hideError();
    setLoading(true);

    try {
        const user = await loadCurrentUser();

        if (!user) {
            return;
        }

        const session = await startTutorSession();

        if (!session) {
            return;
        }

        setLoading(false);

    } catch (error) {
        console.error(
            "Tutor initialization error:",
            error,
        );

        setLoading(false);

        showError(
            error.message
            || "Unable to start the AI tutor session.",
        );
    }
}


async function sendTutorMessage(message) {
    return apiRequest(
        `/student/diagnostic/${diagnosticAttemptId}/tutor/message`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message,
            }),
        },
    );
}


if (tutorForm) {
    tutorForm.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            hideError();

            const message = tutorMessage.value.trim();

            if (!message) {
                showError(
                    "Please enter a question or response.",
                );
                return;
            }

            sendMessageButton.disabled = true;
            sendMessageButton.textContent = "Sending...";

            appendMessage(
                "student",
                message,
            );

            tutorMessage.value = "";

            try {
                const response = await sendTutorMessage(message);

                if (!response) {
                    return;
                }

                appendMessage(
                    "assistant",
                    response.tutor_message,
                );

                tutorMessage.focus();

            } catch (error) {
                console.error(
                    "Tutor message error:",
                    error,
                );

                showError(
                    error.message
                    || "Unable to send your message.",
                );
            } finally {
                sendMessageButton.disabled = false;
                sendMessageButton.textContent = "Send message";
            }
        },
    );
}


if (continuePracticeButton) {
    continuePracticeButton.addEventListener(
        "click",
        () => {
            window.location.href = (
                `/student/diagnostic/${diagnosticAttemptId}/practice`
            );
        },
    );
}


if (logoutButton) {
    logoutButton.addEventListener(
        "click",
        redirectToLogin,
    );
}


initializeTutor();
