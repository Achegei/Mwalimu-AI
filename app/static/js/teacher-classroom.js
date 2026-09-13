const accessToken = localStorage.getItem(
    "mwalimu_access_token",
);

const classroomContent = document.getElementById(
    "teacher-classroom-content",
);

const classroomId = Number(
    classroomContent?.dataset.classroomId,
);

const teacherName = document.getElementById(
    "teacher-name",
);

const logoutButton = document.getElementById(
    "logout-button",
);

const classroomName = document.getElementById(
    "classroom-name",
);

const classroomMeta = document.getElementById(
    "classroom-meta",
);

const classroomError = document.getElementById(
    "teacher-classroom-error",
);

const classroomLoading = document.getElementById(
    "teacher-classroom-loading",
);

const classroomMain = document.getElementById(
    "teacher-classroom-main",
);

const studentCount = document.getElementById(
    "student-count",
);

const diagnosticCount = document.getElementById(
    "diagnostic-count",
);

const practiceCount = document.getElementById(
    "practice-count",
);

const averageDiagnostic = document.getElementById(
    "average-diagnostic",
);

const classStudentList = document.getElementById(
    "class-student-list",
);

const topicPerformanceList = document.getElementById(
    "topic-performance-list",
);

const weaknessSummary = document.getElementById(
    "weakness-summary",
);

const weaknessList = document.getElementById(
    "weakness-list",
);

const teacherInsightLoading = document.getElementById(
    "teacher-insight-loading",
);

const teacherInsightError = document.getElementById(
    "teacher-insight-error",
);

const teacherInsightContent = document.getElementById(
    "teacher-insight-content",
);


function redirectToLogin() {
    localStorage.removeItem("mwalimu_access_token");
    localStorage.removeItem("mwalimu_user");

    window.location.href = "/";
}


function setLoading(isLoading) {
    if (classroomLoading) {
        classroomLoading.hidden = !isLoading;
    }

    if (classroomMain) {
        classroomMain.hidden = isLoading;
    }
}


function showError(message) {
    if (!classroomError) {
        return;
    }

    classroomError.textContent = message;
    classroomError.hidden = false;
}


async function apiRequest(url) {
    const response = await fetch(
        url,
        {
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
        let message = "Unable to load class analytics.";

        try {
            const data = await response.json();

            if (
                data
                && typeof data.detail === "string"
            ) {
                message = data.detail;
            }
        } catch (error) {
            console.error(error);
        }

        throw new Error(message);
    }

    return response.json();
}


function formatScore(value) {
    if (
        value === null
        || value === undefined
    ) {
        return "No data";
    }

    return `${Number(value).toFixed(2)}%`;
}


function getWeaknessLabel(status) {
    switch (status) {
        case "critical":
            return "Critical";

        case "needs_attention":
            return "Needs attention";

        case "satisfactory":
            return "Satisfactory";

        case "insufficient_data":
            return "Insufficient data";

        default:
            return status;
    }
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

    if (teacherName) {
        teacherName.textContent = user.full_name;
    }

    return user;
}


function renderSummary(summary) {
    classroomName.textContent = summary.classroom_name;

    classroomMeta.textContent = (
        `Form ${summary.form_level} · `
        + `${summary.academic_year}`
    );

    studentCount.textContent = summary.student_count;
    diagnosticCount.textContent = summary.completed_diagnostics;
    practiceCount.textContent = summary.completed_practice_attempts;

    averageDiagnostic.textContent = formatScore(
        summary.average_diagnostic_score,
    );
}


function createStudentCard(student) {
    const card = document.createElement("article");
    card.className = "card";

    const title = document.createElement("h3");
    title.className = "card__title";
    title.textContent = student.full_name;

    const loginId = document.createElement("p");
    loginId.className = "text-muted";
    loginId.textContent = (
        `Student ID: ${student.login_id}`
    );

    const link = document.createElement("a");
    link.className = "button button--secondary";
    link.href = (
        `/teacher/classes/${classroomId}`
        + `/students/${student.student_id}`
    );
    link.textContent = "View progress";

    card.appendChild(title);
    card.appendChild(loginId);
    card.appendChild(link);

    return card;
}


function renderClassStudents(students) {
    if (!classStudentList) {
        return;
    }

    classStudentList.innerHTML = "";

    if (
        !Array.isArray(students)
        || students.length === 0
    ) {
        classStudentList.innerHTML = (
            '<div class="empty-state">'
            + '<h3 class="empty-state__title">'
            + 'No enrolled students'
            + '</h3>'
            + '<p class="text-muted mb-0">'
            + 'There are no active students in this class.'
            + '</p>'
            + '</div>'
        );

        return;
    }

    for (const student of students) {
        classStudentList.appendChild(
            createStudentCard(student),
        );
    }
}


function createTopicCard(topic) {
    const card = document.createElement("article");
    card.className = "card";

    const title = document.createElement("h3");
    title.className = "card__title";
    title.textContent = topic.topic_title;

    const assessed = document.createElement("p");
    assessed.className = "text-muted";
    assessed.textContent = (
        `Students assessed: ${topic.students_assessed}`
    );

    const diagnostic = document.createElement("p");
    diagnostic.textContent = (
        "Average diagnostic: "
        + formatScore(topic.average_diagnostic_score)
    );

    const practice = document.createElement("p");
    practice.textContent = (
        "Average practice: "
        + formatScore(topic.average_practice_score)
    );

    const improvement = document.createElement("p");

    if (
        topic.improvement_percentage_points
        === null
        || topic.improvement_percentage_points
        === undefined
    ) {
        improvement.textContent = "Change: No paired data";
    } else {
        improvement.textContent = (
            "Change: "
            + Number(
                topic.improvement_percentage_points,
            ).toFixed(2)
            + " percentage points"
        );
    }

    card.appendChild(title);
    card.appendChild(assessed);
    card.appendChild(diagnostic);
    card.appendChild(practice);
    card.appendChild(improvement);

    return card;
}


function renderTopicPerformance(data) {
    topicPerformanceList.innerHTML = "";

    if (
        !Array.isArray(data.topics)
        || data.topics.length === 0
    ) {
        topicPerformanceList.innerHTML = (
            '<div class="empty-state">'
            + '<h3 class="empty-state__title">'
            + 'No topic data yet'
            + '</h3>'
            + '</div>'
        );

        return;
    }

    for (const topic of data.topics) {
        topicPerformanceList.appendChild(
            createTopicCard(topic),
        );
    }
}


function createWeaknessSummaryCard(label, value) {
    const card = document.createElement("div");
    card.className = "card";

    const description = document.createElement("p");
    description.className = "text-muted mb-1";
    description.textContent = label;

    const number = document.createElement("h3");
    number.className = "mb-0";
    number.textContent = value;

    card.appendChild(description);
    card.appendChild(number);

    return card;
}


function renderWeaknessAnalysis(data) {
    weaknessSummary.innerHTML = "";

    weaknessSummary.appendChild(
        createWeaknessSummaryCard(
            "Assessed topics",
            data.assessed_topic_count,
        ),
    );

    weaknessSummary.appendChild(
        createWeaknessSummaryCard(
            "Weak topics",
            data.weak_topic_count,
        ),
    );

    weaknessSummary.appendChild(
        createWeaknessSummaryCard(
            "Insufficient data",
            data.insufficient_data_topic_count,
        ),
    );

    weaknessList.innerHTML = "";

    for (const topic of data.topics) {
        const card = document.createElement("article");
        card.className = "card";

        const title = document.createElement("h3");
        title.className = "card__title";
        title.textContent = topic.topic_title;

        const status = document.createElement("p");
        status.className = "mb-1";
        status.textContent = (
            "Status: "
            + getWeaknessLabel(
                topic.weakness_status,
            )
        );

        const score = document.createElement("p");
        score.className = "text-muted mb-0";
        score.textContent = (
            "Average diagnostic: "
            + formatScore(
                topic.average_diagnostic_score,
            )
        );

        card.appendChild(title);
        card.appendChild(status);
        card.appendChild(score);

        weaknessList.appendChild(card);
    }
}


function createInsightCard(titleText, bodyText) {
    const card = document.createElement("article");
    card.className = "card";

    const title = document.createElement("h3");
    title.className = "card__title";
    title.textContent = titleText;

    const body = document.createElement("p");
    body.className = "mb-0";
    body.textContent = bodyText;

    card.appendChild(title);
    card.appendChild(body);

    return card;
}


function renderTeacherInsight(data) {
    if (
        !teacherInsightContent
        || !teacherInsightLoading
        || !teacherInsightError
    ) {
        return;
    }

    teacherInsightLoading.hidden = true;
    teacherInsightError.hidden = true;
    teacherInsightContent.hidden = false;

    teacherInsightContent.innerHTML = "";

    const insight = data.insight;

    teacherInsightContent.appendChild(
        createInsightCard(
            "Class summary",
            insight.teacher_summary,
        ),
    );

    teacherInsightContent.appendChild(
        createInsightCard(
            "Main learning concern",
            insight.main_learning_concern,
        ),
    );

    teacherInsightContent.appendChild(
        createInsightCard(
            "Suggested intervention",
            insight.suggested_intervention,
        ),
    );

    teacherInsightContent.appendChild(
        createInsightCard(
            "Follow-up recommendation",
            insight.follow_up_recommendation,
        ),
    );
}


async function loadTeacherInsight() {
    try {
        const data = await apiRequest(
            `/teacher/classes/${classroomId}/insight`,
        );

        if (!data) {
            return;
        }

        renderTeacherInsight(data);

    } catch (error) {
        console.error(
            "Teacher insight error:",
            error,
        );

        if (teacherInsightLoading) {
            teacherInsightLoading.hidden = true;
        }

        if (teacherInsightError) {
            teacherInsightError.hidden = false;
            teacherInsightError.textContent = (
                error.message
                || "Unable to generate teaching insight."
            );
        }
    }
}


async function initializeClassroom() {
    if (!accessToken) {
        redirectToLogin();
        return;
    }

    setLoading(true);

    try {
        const user = await loadCurrentUser();

        if (!user) {
            return;
        }

        const [
            summary,
            students,
            topics,
            weaknesses,
        ] = await Promise.all([
            apiRequest(
                `/teacher/classes/${classroomId}/summary`,
            ),
            apiRequest(
                `/teacher/classes/${classroomId}/students`,
            ),
            apiRequest(
                `/teacher/classes/${classroomId}/topics`,
            ),
            apiRequest(
                `/teacher/classes/${classroomId}/weak-topics`,
            ),
        ]);

        renderSummary(summary);
        renderClassStudents(students);
        renderTopicPerformance(topics);
        renderWeaknessAnalysis(weaknesses);

        await loadTeacherInsight();

        setLoading(false);

    } catch (error) {
        console.error(
            "Teacher classroom error:",
            error,
        );

        setLoading(false);

        showError(
            error.message
            || "Unable to load class analytics.",
        );
    }
}


if (logoutButton) {
    logoutButton.addEventListener(
        "click",
        redirectToLogin,
    );
}


initializeClassroom();
