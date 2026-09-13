const accessToken = localStorage.getItem(
    "mwalimu_access_token",
);

const page = document.getElementById(
    "teacher-student-progress",
);

const classroomId = Number(
    page?.dataset.classroomId,
);

const studentId = Number(
    page?.dataset.studentId,
);

const pageTitle = document.getElementById(
    "student-progress-name",
);

const pageContext = document.getElementById(
    "student-progress-context",
);

const errorElement = document.getElementById(
    "student-progress-error",
);

const loadingElement = document.getElementById(
    "student-progress-loading",
);

const mainElement = document.getElementById(
    "student-progress-main",
);

const studentName = document.getElementById(
    "student-name",
);

const studentLoginId = document.getElementById(
    "student-login-id",
);

const classroomName = document.getElementById(
    "student-classroom-name",
);

const completedCount = document.getElementById(
    "student-completed-count",
);

const improvedCount = document.getElementById(
    "student-improved-count",
);

const unchangedCount = document.getElementById(
    "student-unchanged-count",
);

const declinedCount = document.getElementById(
    "student-declined-count",
);

const progressEmpty = document.getElementById(
    "student-progress-empty",
);

const progressList = document.getElementById(
    "student-progress-list",
);


function redirectToLogin() {
    localStorage.removeItem("mwalimu_access_token");
    localStorage.removeItem("mwalimu_user");

    window.location.href = "/";
}


function showError(message) {
    if (!errorElement) {
        return;
    }

    errorElement.textContent = message;
    errorElement.hidden = false;
}


function hideError() {
    if (!errorElement) {
        return;
    }

    errorElement.textContent = "";
    errorElement.hidden = true;
}


function setLoading(isLoading) {
    if (loadingElement) {
        loadingElement.hidden = !isLoading;
    }

    if (mainElement) {
        mainElement.hidden = isLoading;
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
        let message = "Unable to load student progress.";

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


async function verifyTeacher() {
    const user = await apiRequest("/auth/me");

    if (!user) {
        return null;
    }

    if (user.role !== "teacher") {
        localStorage.removeItem("mwalimu_access_token");
        localStorage.removeItem("mwalimu_user");

        window.location.href = "/";
        return null;
    }

    localStorage.setItem(
        "mwalimu_user",
        JSON.stringify(user),
    );

    return user;
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


function getLearningStatusClass(status) {
    switch (status) {
        case "improved":
            return "badge badge--success";

        case "unchanged":
            return "badge badge--warning";

        case "declined":
            return "badge badge--danger";

        default:
            return "badge badge--info";
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
        return (
            `+${numericChange.toFixed(2)}`
            + " percentage points"
        );
    }

    return (
        `${numericChange.toFixed(2)}`
        + " percentage points"
    );
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

    const heading = document.createElement("div");

    const subject = document.createElement("p");
    subject.className = "text-muted mb-1";
    subject.textContent = progress.subject_name;

    const title = document.createElement("h3");
    title.className = "card__title";
    title.textContent = progress.topic_title;

    heading.appendChild(subject);
    heading.appendChild(title);

    const status = document.createElement("span");
    status.className = getLearningStatusClass(
        progress.learning_status,
    );
    status.textContent = getLearningStatusLabel(
        progress.learning_status,
    );

    header.appendChild(heading);
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


function renderStudent(data) {
    if (pageTitle) {
        pageTitle.textContent = (
            `${data.student.full_name}'s Progress`
        );
    }

    if (pageContext) {
        pageContext.textContent = (
            `Learning progress in ${data.classroom_name}.`
        );
    }

    if (studentName) {
        studentName.textContent = data.student.full_name;
    }

    if (studentLoginId) {
        studentLoginId.textContent = (
            `Student ID: ${data.student.login_id}`
        );
    }

    if (classroomName) {
        classroomName.textContent = (
            `Class: ${data.classroom_name}`
        );
    }
}


function renderProgress(progress) {
    if (completedCount) {
        completedCount.textContent = (
            progress.completed_topics ?? 0
        );
    }

    if (improvedCount) {
        improvedCount.textContent = (
            progress.improved_topics ?? 0
        );
    }

    if (unchangedCount) {
        unchangedCount.textContent = (
            progress.unchanged_topics ?? 0
        );
    }

    if (declinedCount) {
        declinedCount.textContent = (
            progress.declined_topics ?? 0
        );
    }

    const topics = Array.isArray(progress.topics)
        ? progress.topics
        : [];

    if (!progressList || !progressEmpty) {
        return;
    }

    progressList.innerHTML = "";

    if (topics.length === 0) {
        progressList.hidden = true;
        progressEmpty.hidden = false;
        return;
    }

    progressEmpty.hidden = true;
    progressList.hidden = false;

    for (const topic of topics) {
        progressList.appendChild(
            createProgressCard(topic),
        );
    }
}


async function loadStudentProgress() {
    return apiRequest(
        `/teacher/classes/${classroomId}`
        + `/students/${studentId}/progress`,
    );
}


async function initializePage() {
    if (!accessToken) {
        redirectToLogin();
        return;
    }

    if (
        !Number.isInteger(classroomId)
        || classroomId <= 0
        || !Number.isInteger(studentId)
        || studentId <= 0
    ) {
        setLoading(false);

        showError(
            "Invalid classroom or student identifier.",
        );

        return;
    }

    hideError();
    setLoading(true);

    try {
        const user = await verifyTeacher();

        if (!user) {
            return;
        }

        const data = await loadStudentProgress();

        if (!data) {
            return;
        }

        renderStudent(data);
        renderProgress(data.progress);

        setLoading(false);

    } catch (error) {
        console.error(
            "Teacher student progress error:",
            error,
        );

        setLoading(false);

        showError(
            error.message
            || "Unable to load student progress.",
        );
    }
}


initializePage();
