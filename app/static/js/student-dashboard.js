const accessToken = localStorage.getItem("mwalimu_access_token");

const studentName = document.getElementById("student-name");
const logoutButton = document.getElementById("logout-button");

const dashboardError = document.getElementById(
    "student-dashboard-error",
);

const dashboardLoading = document.getElementById(
    "student-dashboard-loading",
);

const dashboardMain = document.getElementById(
    "student-dashboard-main",
);

const subjectGrid = document.getElementById("subject-grid");

const progressContent = document.getElementById(
    "progress-content",
);

const progressEmpty = document.getElementById(
    "progress-empty",
);

const progressList = document.getElementById(
    "progress-list",
);

const progressCompletedCount = document.getElementById(
    "progress-completed-count",
);

const progressImprovedCount = document.getElementById(
    "progress-improved-count",
);

const progressUnchangedCount = document.getElementById(
    "progress-unchanged-count",
);

const progressDeclinedCount = document.getElementById(
    "progress-declined-count",
);


function redirectToLogin() {
    localStorage.removeItem("mwalimu_access_token");
    localStorage.removeItem("mwalimu_user");

    window.location.href = "/";
}


function showDashboardError(message) {
    if (!dashboardError) {
        return;
    }

    dashboardError.textContent = message;
    dashboardError.hidden = false;
}


function hideDashboardError() {
    if (!dashboardError) {
        return;
    }

    dashboardError.textContent = "";
    dashboardError.hidden = true;
}


function setDashboardLoading(isLoading) {
    if (dashboardLoading) {
        dashboardLoading.hidden = !isLoading;
    }

    if (dashboardMain) {
        dashboardMain.hidden = isLoading;
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

    if (!response.ok) {
        let message = "Unable to load data.";

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
        localStorage.removeItem("mwalimu_access_token");
        localStorage.removeItem("mwalimu_user");

        window.location.href = "/";
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


function createSubjectCard(subject) {
    const card = document.createElement("article");
    card.className = "card subject-card";

    const title = document.createElement("h3");
    title.className = "card__title";
    title.textContent = subject.name;

    const description = document.createElement("p");
    description.className = "card__description";
    description.textContent = (
        subject.description
        || "View available learning topics for this subject."
    );

    const footer = document.createElement("div");
    footer.className = "card__footer";

    const link = document.createElement("a");
    link.className = "button button--primary";
    link.href = `/student/subjects/${subject.id}`;
    link.textContent = "View topics";

    footer.appendChild(link);

    card.appendChild(title);
    card.appendChild(description);
    card.appendChild(footer);

    return card;
}


function renderSubjects(subjects) {
    if (!subjectGrid) {
        return;
    }

    subjectGrid.innerHTML = "";

    if (!Array.isArray(subjects) || subjects.length === 0) {
        const emptyState = document.createElement("div");
        emptyState.className = "empty-state";

        const title = document.createElement("h3");
        title.className = "empty-state__title";
        title.textContent = "No subjects available";

        const description = document.createElement("p");
        description.className = "empty-state__description";
        description.textContent = (
            "There are currently no subjects assigned "
            + "to your learning account."
        );

        emptyState.appendChild(title);
        emptyState.appendChild(description);

        subjectGrid.appendChild(emptyState);
        return;
    }

    for (const subject of subjects) {
        subjectGrid.appendChild(
            createSubjectCard(subject),
        );
    }
}


async function loadSubjects() {
    const subjects = await apiRequest(
        "/student/subjects",
    );

    if (!subjects) {
        return;
    }

    renderSubjects(subjects);
}


function getLearningStatusLabel(status) {
    switch (status) {
        case "improved":
            return "Improved";

        case "unchanged":
            return "Unchanged";

        case "declined":
            return "Needs attention";

        case "diagnostic_completed":
            return "Diagnostic completed";

        default:
            return "Learning activity";
    }
}


function formatScore(score) {
    if (
        score === null
        || score === undefined
    ) {
        return "Not completed";
    }

    return `${Number(score).toFixed(2)}%`;
}


function formatImprovement(change) {
    if (
        change === null
        || change === undefined
    ) {
        return "Practice not completed";
    }

    const numericChange = Number(change);

    if (numericChange > 0) {
        return `+${numericChange.toFixed(2)} percentage points`;
    }

    return `${numericChange.toFixed(2)} percentage points`;
}


function formatActivityDate(value) {
    if (!value) {
        return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "";
    }

    return date.toLocaleDateString(
        undefined,
        {
            year: "numeric",
            month: "short",
            day: "numeric",
        },
    );
}


function createProgressCard(progress) {
    const card = document.createElement("article");
    card.className = "card";

    const header = document.createElement("div");
    header.className = "card__header";

    const subject = document.createElement("p");
    subject.className = "text-muted mb-1";
    subject.textContent = progress.subject_name;

    const title = document.createElement("h3");
    title.className = "card__title";
    title.textContent = progress.topic_title;

    const status = document.createElement("span");
    status.className = "badge";
    status.textContent = getLearningStatusLabel(
        progress.learning_status,
    );

    header.appendChild(subject);
    header.appendChild(title);
    header.appendChild(status);

    const scores = document.createElement("div");
    scores.className = "grid grid--2 mt-2";

    const diagnosticBlock = document.createElement("div");

    const diagnosticLabel = document.createElement("p");
    diagnosticLabel.className = "text-muted mb-1";
    diagnosticLabel.textContent = "Diagnostic";

    const diagnosticScore = document.createElement("strong");
    diagnosticScore.textContent = formatScore(
        progress.diagnostic_score,
    );

    diagnosticBlock.appendChild(diagnosticLabel);
    diagnosticBlock.appendChild(diagnosticScore);

    const practiceBlock = document.createElement("div");

    const practiceLabel = document.createElement("p");
    practiceLabel.className = "text-muted mb-1";
    practiceLabel.textContent = "Practice";

    const practiceScore = document.createElement("strong");
    practiceScore.textContent = formatScore(
        progress.practice_score,
    );

    practiceBlock.appendChild(practiceLabel);
    practiceBlock.appendChild(practiceScore);

    scores.appendChild(diagnosticBlock);
    scores.appendChild(practiceBlock);

    const improvement = document.createElement("p");
    improvement.className = "mt-2 mb-1";
    improvement.textContent = (
        "Change: "
        + formatImprovement(
            progress.improvement_percentage_points,
        )
    );

    const activityDate = document.createElement("p");
    activityDate.className = "text-muted mb-0";

    const formattedDate = formatActivityDate(
        progress.completed_at,
    );

    if (formattedDate) {
        activityDate.textContent = (
            `Latest activity: ${formattedDate}`
        );
    }

    card.appendChild(header);
    card.appendChild(scores);
    card.appendChild(improvement);

    if (formattedDate) {
        card.appendChild(activityDate);
    }

    return card;
}


function renderProgress(progress) {
    if (
        !progressContent
        || !progressEmpty
        || !progressList
    ) {
        return;
    }

    const topics = Array.isArray(progress.topics)
        ? progress.topics
        : [];

    if (topics.length === 0) {
        progressContent.hidden = true;
        progressEmpty.hidden = false;
        progressList.innerHTML = "";
        return;
    }

    progressEmpty.hidden = true;
    progressContent.hidden = false;

    if (progressCompletedCount) {
        progressCompletedCount.textContent = (
            progress.completed_topics ?? 0
        );
    }

    if (progressImprovedCount) {
        progressImprovedCount.textContent = (
            progress.improved_topics ?? 0
        );
    }

    if (progressUnchangedCount) {
        progressUnchangedCount.textContent = (
            progress.unchanged_topics ?? 0
        );
    }

    if (progressDeclinedCount) {
        progressDeclinedCount.textContent = (
            progress.declined_topics ?? 0
        );
    }

    progressList.innerHTML = "";

    for (const topic of topics) {
        progressList.appendChild(
            createProgressCard(topic),
        );
    }
}


async function loadProgress() {
    const progress = await apiRequest(
        "/student/progress",
    );

    if (!progress) {
        return;
    }

    renderProgress(progress);
}


async function initializeDashboard() {
    if (!accessToken) {
        redirectToLogin();
        return;
    }

    hideDashboardError();
    setDashboardLoading(true);

    try {
        const user = await loadCurrentUser();

        if (!user) {
            return;
        }

        await Promise.all([
            loadSubjects(),
            loadProgress(),
        ]);

        setDashboardLoading(false);

    } catch (error) {
        console.error(
            "Student dashboard error:",
            error,
        );

        setDashboardLoading(false);

        showDashboardError(
            error.message
            || "Unable to load your dashboard.",
        );
    }
}


if (logoutButton) {
    logoutButton.addEventListener(
        "click",
        redirectToLogin,
    );
}


initializeDashboard();
