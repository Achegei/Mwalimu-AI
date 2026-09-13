const accessToken = localStorage.getItem(
    "mwalimu_access_token",
);

const teacherName = document.getElementById(
    "teacher-name",
);

const logoutButton = document.getElementById(
    "logout-button",
);

const dashboardError = document.getElementById(
    "teacher-dashboard-error",
);

const dashboardLoading = document.getElementById(
    "teacher-dashboard-loading",
);

const dashboardMain = document.getElementById(
    "teacher-dashboard-main",
);

const classGrid = document.getElementById(
    "teacher-class-grid",
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
        let message = "Unable to load teacher data.";

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

    if (user.role !== "teacher") {
        redirectToLogin();
        return null;
    }

    localStorage.setItem(
        "mwalimu_user",
        JSON.stringify(user),
    );

    if (teacherName) {
        teacherName.textContent = user.full_name;
    }

    return user;
}


function createClassCard(classroom) {
    const card = document.createElement("article");
    card.className = "card";

    const eyebrow = document.createElement("p");
    eyebrow.className = "text-muted mb-1";
    eyebrow.textContent = (
        `Form ${classroom.form_level} · `
        + `${classroom.academic_year}`
    );

    const title = document.createElement("h3");
    title.className = "card__title";
    title.textContent = classroom.name;

    const description = document.createElement("p");
    description.className = "card__description";
    description.textContent = (
        "View class learning activity, topic performance, "
        + "weakness analysis, and intervention insights."
    );

    const footer = document.createElement("div");
    footer.className = "card__footer";

    const link = document.createElement("a");
    link.className = "button button--primary";
    link.href = `/teacher/classes/${classroom.id}`;
    link.textContent = "View class analytics";

    footer.appendChild(link);

    card.appendChild(eyebrow);
    card.appendChild(title);
    card.appendChild(description);
    card.appendChild(footer);

    return card;
}


function renderClasses(classes) {
    if (!classGrid) {
        return;
    }

    classGrid.innerHTML = "";

    if (!Array.isArray(classes) || classes.length === 0) {
        const emptyState = document.createElement("div");
        emptyState.className = "empty-state";

        const title = document.createElement("h3");
        title.className = "empty-state__title";
        title.textContent = "No classes available";

        const description = document.createElement("p");
        description.className = "empty-state__description";
        description.textContent = (
            "There are currently no classes assigned "
            + "to your teacher account."
        );

        emptyState.appendChild(title);
        emptyState.appendChild(description);

        classGrid.appendChild(emptyState);
        return;
    }

    for (const classroom of classes) {
        classGrid.appendChild(
            createClassCard(classroom),
        );
    }
}


async function loadClasses() {
    const classes = await apiRequest(
        "/teacher/classes",
    );

    if (!classes) {
        return;
    }

    renderClasses(classes);
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

        await loadClasses();

        setDashboardLoading(false);

    } catch (error) {
        console.error(
            "Teacher dashboard error:",
            error,
        );

        setDashboardLoading(false);

        showDashboardError(
            error.message
            || "Unable to load your teacher dashboard.",
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
