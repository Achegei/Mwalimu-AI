const accessToken = localStorage.getItem("mwalimu_access_token");
const subjectId = window.MWALIMU_SUBJECT_ID;

const studentName = document.getElementById("student-name");
const logoutButton = document.getElementById("logout-button");

const subjectTitle = document.getElementById("subject-title");
const subjectDescription = document.getElementById(
    "subject-description",
);

const subjectError = document.getElementById("subject-error");
const subjectLoading = document.getElementById("subject-loading");
const subjectMain = document.getElementById("subject-main");
const topicGrid = document.getElementById("topic-grid");


function redirectToLogin() {
    localStorage.removeItem("mwalimu_access_token");
    localStorage.removeItem("mwalimu_user");

    window.location.href = "/";
}


function showError(message) {
    if (!subjectError) {
        return;
    }

    subjectError.textContent = message;
    subjectError.hidden = false;
}


function hideError() {
    if (!subjectError) {
        return;
    }

    subjectError.textContent = "";
    subjectError.hidden = true;
}


function setLoading(isLoading) {
    if (subjectLoading) {
        subjectLoading.hidden = !isLoading;
    }

    if (subjectMain) {
        subjectMain.hidden = isLoading;
    }
}


async function apiRequest(url) {
    const response = await fetch(
        url,
        {
            method: "GET",
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
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
        let message = "Unable to load data.";

        try {
            const data = await response.json();

            if (
                data &&
                typeof data.detail === "string"
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


function createTopicCard(topic) {
    const card = document.createElement("article");
    card.className = "card topic-card";

    const header = document.createElement("div");
    header.className = "card__header";

    const title = document.createElement("h3");
    title.className = "card__title";
    title.textContent = topic.title;

    const description = document.createElement("p");
    description.className = "card__description";
    description.textContent = (
        topic.summary
        || "Begin with a diagnostic to identify your learning needs."
    );

    header.appendChild(title);
    header.appendChild(description);

    const footer = document.createElement("div");
    footer.className = "card__footer";

    const button = document.createElement("a");
    button.className = "button button--primary";
    button.href = `/student/topics/${topic.id}/diagnostic`;
    button.textContent = "Start diagnostic";

    footer.appendChild(button);

    card.appendChild(header);
    card.appendChild(footer);

    return card;
}


function renderTopics(topics) {
    if (!topicGrid) {
        return;
    }

    topicGrid.innerHTML = "";

    if (!Array.isArray(topics) || topics.length === 0) {
        const emptyState = document.createElement("div");
        emptyState.className = "empty-state";

        const title = document.createElement("h3");
        title.className = "empty-state__title";
        title.textContent = "No topics available";

        const description = document.createElement("p");
        description.className = "empty-state__description";
        description.textContent = (
            "There are currently no learning topics "
            + "available for this subject."
        );

        emptyState.appendChild(title);
        emptyState.appendChild(description);

        topicGrid.appendChild(emptyState);
        return;
    }

    for (const topic of topics) {
        topicGrid.appendChild(
            createTopicCard(topic),
        );
    }
}


function setSubjectInformation(subject) {
    if (!subject) {
        return;
    }

    if (
        subjectTitle
        && subject.name
    ) {
        subjectTitle.textContent = subject.name;
    }

    if (
        subjectDescription
        && subject.description
    ) {
        subjectDescription.textContent =
            subject.description;
    }
}


async function loadTopics() {
    const subject = await apiRequest(
        `/student/subjects/${subjectId}/topics`,
    );

    if (!subject) {
        return;
    }

    setSubjectInformation(subject);
    renderTopics(subject.topics);
}


async function initializeSubjectPage() {
    if (!accessToken) {
        redirectToLogin();
        return;
    }

    if (!subjectId) {
        setLoading(false);

        showError(
            "The requested subject could not be identified.",
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

        await loadTopics();

        setLoading(false);

    } catch (error) {
        console.error(
            "Subject page error:",
            error,
        );

        setLoading(false);

        showError(
            error.message
            || "Unable to load this subject.",
        );
    }
}


if (logoutButton) {
    logoutButton.addEventListener(
        "click",
        redirectToLogin,
    );
}


initializeSubjectPage();
