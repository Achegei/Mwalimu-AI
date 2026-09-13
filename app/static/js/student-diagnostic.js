const accessToken = localStorage.getItem("mwalimu_access_token");
const topicId = window.MWALIMU_TOPIC_ID;

const studentName = document.getElementById("student-name");
const logoutButton = document.getElementById("logout-button");

const diagnosticTitle = document.getElementById(
    "diagnostic-title",
);

const diagnosticDescription = document.getElementById(
    "diagnostic-description",
);

const diagnosticError = document.getElementById(
    "diagnostic-error",
);

const diagnosticLoading = document.getElementById(
    "diagnostic-loading",
);

const diagnosticMain = document.getElementById(
    "diagnostic-main",
);

const questionProgress = document.getElementById(
    "question-progress",
);

const questionText = document.getElementById(
    "question-text",
);

const answerOptions = document.getElementById(
    "answer-options",
);

const diagnosticForm = document.getElementById(
    "diagnostic-form",
);

const submitAnswerButton = document.getElementById(
    "submit-answer-button",
);


let diagnosticAttempt = null;
let currentQuestionIndex = 0;


function redirectToLogin() {
    localStorage.removeItem("mwalimu_access_token");
    localStorage.removeItem("mwalimu_user");

    window.location.href = "/";
}


function showError(message) {
    if (!diagnosticError) {
        return;
    }

    diagnosticError.textContent = message;
    diagnosticError.hidden = false;
}


function hideError() {
    if (!diagnosticError) {
        return;
    }

    diagnosticError.textContent = "";
    diagnosticError.hidden = true;
}


function setLoading(isLoading) {
    if (diagnosticLoading) {
        diagnosticLoading.hidden = !isLoading;
    }

    if (diagnosticMain) {
        diagnosticMain.hidden = isLoading;
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


function createAnswerOption(
    question,
    option,
    index,
) {
    const wrapper = document.createElement("label");
    wrapper.className = "card";

    const layout = document.createElement("div");
    layout.className = "flex items-center gap-2";

    const input = document.createElement("input");
    input.type = "radio";
    input.name = "diagnostic-answer";
    input.value = option;
    input.required = true;

    input.id = (
        `diagnostic-answer-${question.id}-${index}`
    );

    const text = document.createElement("span");
    text.textContent = option;

    layout.appendChild(input);
    layout.appendChild(text);

    wrapper.appendChild(layout);

    return wrapper;
}


function renderQuestion() {
    if (
        !diagnosticAttempt
        || !Array.isArray(diagnosticAttempt.questions)
    ) {
        return;
    }

    const questions = diagnosticAttempt.questions;

    if (questions.length === 0) {
        showError(
            "No diagnostic questions are available for this topic.",
        );

        return;
    }

    const question = questions[currentQuestionIndex];

    if (!question) {
        showError(
            "The requested diagnostic question could not be loaded.",
        );

        return;
    }

    if (questionProgress) {
        questionProgress.textContent = (
            `Question ${currentQuestionIndex + 1} `
            + `of ${diagnosticAttempt.total_questions}`
        );
    }

    if (questionText) {
        questionText.textContent = question.prompt;
    }

    if (!answerOptions) {
        return;
    }

    answerOptions.innerHTML = "";

    const options = Array.isArray(question.options)
        ? question.options
        : [];

    if (options.length === 0) {
        showError(
            "This question does not contain answer options.",
        );

        return;
    }

    options.forEach(
        (option, index) => {
            answerOptions.appendChild(
                createAnswerOption(
                    question,
                    option,
                    index,
                ),
            );
        },
    );
}


async function startDiagnostic() {
    const diagnostic = await apiRequest(
        `/student/topics/${topicId}/diagnostic/start`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        },
    );

    if (!diagnostic) {
        return null;
    }

    diagnosticAttempt = diagnostic;
    currentQuestionIndex = 0;

    if (diagnosticTitle) {
        diagnosticTitle.textContent =
            diagnostic.topic_title;
    }

    if (diagnosticDescription) {
        diagnosticDescription.textContent = (
            "Complete this short diagnostic assessment "
            + "so Mwalimu AI can identify where you "
            + "need the most support."
        );
    }

    renderQuestion();

    return diagnostic;
}


async function initializeDiagnostic() {
    if (!accessToken) {
        redirectToLogin();
        return;
    }

    if (!topicId) {
        setLoading(false);

        showError(
            "The requested topic could not be identified.",
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

        const diagnostic = await startDiagnostic();

        if (!diagnostic) {
            return;
        }

        setLoading(false);

    } catch (error) {
        console.error(
            "Diagnostic initialization error:",
            error,
        );

        setLoading(false);

        showError(
            error.message
            || "Unable to start the diagnostic assessment.",
        );
    }
}


async function completeDiagnostic() {
    return apiRequest(
        `/student/diagnostic/${diagnosticAttempt.attempt_id}/complete`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        },
    );
}


async function loadInterpretation() {
    return apiRequest(
        `/student/diagnostic/${diagnosticAttempt.attempt_id}/interpretation`,
    );
}


async function submitCurrentAnswer(event) {
    event.preventDefault();

    hideError();

    if (
        !diagnosticAttempt
        || !Array.isArray(diagnosticAttempt.questions)
    ) {
        showError(
            "Diagnostic data is not available.",
        );

        return;
    }

    const question = diagnosticAttempt.questions[
        currentQuestionIndex
    ];

    if (!question) {
        showError(
            "The current question could not be identified.",
        );

        return;
    }

    const selectedAnswer = document.querySelector(
        'input[name="diagnostic-answer"]:checked',
    );

    if (!selectedAnswer) {
        showError(
            "Select an answer before continuing.",
        );

        return;
    }

    if (submitAnswerButton) {
        submitAnswerButton.disabled = true;
        submitAnswerButton.textContent = "Submitting...";
    }

    try {
        await apiRequest(
            `/student/diagnostic/${diagnosticAttempt.attempt_id}/answer`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    question_id: question.id,
                    answer: selectedAnswer.value,
                }),
            },
        );

        currentQuestionIndex += 1;

        if (
            currentQuestionIndex
            < diagnosticAttempt.questions.length
        ) {
            renderQuestion();

            return;
        }

        const completion = await completeDiagnostic();

        const interpretation = await loadInterpretation();

        if (questionProgress) {
            questionProgress.textContent =
                "Diagnostic complete";
        }

        if (questionText) {
            questionText.textContent = (
                `You scored ${completion.correct_answers} `
                + `out of ${completion.total_questions} `
                + `(${completion.score_percentage}%).`
            );
        }

        if (answerOptions) {
            answerOptions.innerHTML = "";

            const result = document.createElement("div");
            result.className = "card";

            const performance = document.createElement("h3");
            performance.className = "card__title";
            performance.textContent = (
                `Performance level: ${interpretation.performance_level}`
            );

            const message = document.createElement("p");
            message.className = "card__description";

            if (
                Array.isArray(interpretation.weak_questions)
                && interpretation.weak_questions.length > 0
            ) {
                message.textContent = (
                    "Mwalimu AI identified some areas that need more attention."
                );
            } else {
                message.textContent = (
                    "You showed strong understanding in this diagnostic."
                );
            }

            result.appendChild(performance);
            result.appendChild(message);

            answerOptions.appendChild(result);
        }

        if (submitAnswerButton) {
            submitAnswerButton.hidden = true;
            submitAnswerButton.style.display = "none";
        }

    } catch (error) {
        console.error(
            "Diagnostic answer error:",
            error,
        );

        showError(
            error.message
            || "Unable to submit your answer.",
        );

    } finally {
        if (
            submitAnswerButton
            && !submitAnswerButton.hidden
        ) {
            submitAnswerButton.disabled = false;
            submitAnswerButton.textContent =
                "Submit answer";
        }
    }
}


if (diagnosticForm) {
    diagnosticForm.addEventListener(
        "submit",
        submitCurrentAnswer,
    );
}


if (logoutButton) {
    logoutButton.addEventListener(
        "click",
        redirectToLogin,
    );
}


initializeDiagnostic();
