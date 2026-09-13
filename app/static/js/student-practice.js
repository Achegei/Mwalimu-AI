const accessToken = localStorage.getItem("mwalimu_access_token");

const diagnosticAttemptId =
    window.MWALIMU_DIAGNOSTIC_ATTEMPT_ID;

const studentName = document.getElementById("student-name");
const logoutButton = document.getElementById("logout-button");

const practiceError = document.getElementById("practice-error");
const practiceLoading = document.getElementById("practice-loading");
const practiceMain = document.getElementById("practice-main");

const practiceTitle = document.getElementById("practice-title");
const questionProgress = document.getElementById("question-progress");
const questionText = document.getElementById("question-text");
const answerOptions = document.getElementById("answer-options");

const practiceForm = document.getElementById("practice-form");
const submitAnswerButton = document.getElementById(
    "submit-answer-button",
);

let practiceAttempt = null;
let currentQuestionIndex = 0;


function redirectToLogin() {
    localStorage.removeItem("mwalimu_access_token");
    localStorage.removeItem("mwalimu_user");

    window.location.href = "/";
}


function showError(message) {
    if (!practiceError) {
        return;
    }

    practiceError.textContent = message;
    practiceError.hidden = false;
}


function hideError() {
    if (!practiceError) {
        return;
    }

    practiceError.textContent = "";
    practiceError.hidden = true;
}


function setLoading(isLoading) {
    if (practiceLoading) {
        practiceLoading.hidden = !isLoading;
    }

    if (practiceMain) {
        practiceMain.hidden = isLoading;
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


async function startPractice() {
    return apiRequest(
        `/student/diagnostic/${diagnosticAttemptId}/practice/start`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        },
    );
}


function renderQuestion() {
    if (
        !practiceAttempt
        || !Array.isArray(practiceAttempt.questions)
        || practiceAttempt.questions.length === 0
    ) {
        showError(
            "No practice questions are available.",
        );
        return;
    }

    const question =
        practiceAttempt.questions[currentQuestionIndex];

    questionProgress.textContent = (
        `Question ${currentQuestionIndex + 1} `
        + `of ${practiceAttempt.total_questions}`
    );

    questionText.textContent = question.prompt;

    answerOptions.innerHTML = "";

    question.options.forEach(
        (option, index) => {
            const wrapper = document.createElement("label");
            wrapper.className = "answer-option";

            const input = document.createElement("input");
            input.type = "radio";
            input.name = "answer";
            input.value = option;
            input.required = true;

            const text = document.createElement("span");
            text.className = "answer-option__text";
            text.textContent = option;

            wrapper.appendChild(input);
            wrapper.appendChild(text);

            answerOptions.appendChild(wrapper);
        },
    );

    submitAnswerButton.disabled = false;
    submitAnswerButton.textContent = "Submit answer";
}


async function initializePractice() {
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

        const practice = await startPractice();

        if (!practice) {
            return;
        }

        practiceAttempt = practice;
        currentQuestionIndex = 0;

        if (practiceTitle) {
            practiceTitle.textContent = (
                `${practice.topic_title} Practice`
            );
        }

        setLoading(false);
        renderQuestion();

    } catch (error) {
        console.error(
            "Practice initialization error:",
            error,
        );

        setLoading(false);

        showError(
            error.message
            || "Unable to start the practice session.",
        );
    }
}


async function submitPracticeAnswer(
    questionId,
    submittedAnswer,
) {
    return apiRequest(
        `/student/practice/${practiceAttempt.attempt_id}/answer`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                question_id: questionId,
                submitted_answer: submittedAnswer,
            }),
        },
    );
}


async function completePractice() {
    return apiRequest(
        `/student/practice/${practiceAttempt.attempt_id}/complete`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        },
    );
}


async function loadImprovement() {
    return apiRequest(
        `/student/diagnostic/${diagnosticAttemptId}/improvement`,
    );
}


function renderPracticeResult(
    completion,
    improvement,
) {
    questionProgress.textContent = "Practice complete";

    questionText.textContent = (
        `You scored ${completion.correct_answers} `
        + `out of ${completion.total_questions}.`
    );

    answerOptions.innerHTML = "";

    const resultCard = document.createElement("div");
    resultCard.className = "card";

    const scoreTitle = document.createElement("h3");
    scoreTitle.className = "card__title";
    scoreTitle.textContent = (
        `Practice score: ${improvement.practice_score}%`
    );

    const diagnosticScore = document.createElement("p");
    diagnosticScore.className = "card__description";
    diagnosticScore.textContent = (
        `Diagnostic score: ${improvement.diagnostic_score}%`
    );

    const change = document.createElement("p");
    change.className = "card__description";
    change.textContent = (
        `Change: ${improvement.improvement_percentage_points} `
        + "percentage points"
    );

    const status = document.createElement("p");
    status.className = "card__description";
    status.textContent = (
        `Learning status: ${improvement.learning_status}`
    );

    const message = document.createElement("p");
    message.className = "card__description";
    message.textContent = improvement.message;

    const recommendation = document.createElement("p");
    recommendation.className = "card__description";
    recommendation.textContent = (
        `Recommended next step: ${improvement.recommended_action}`
    );

    const dashboardLink = document.createElement("a");
    dashboardLink.href = "/student/dashboard";
    dashboardLink.className = "button button--secondary mt-3";
    dashboardLink.textContent = "Return to dashboard";

    resultCard.appendChild(scoreTitle);
    resultCard.appendChild(diagnosticScore);
    resultCard.appendChild(change);
    resultCard.appendChild(status);
    resultCard.appendChild(message);
    resultCard.appendChild(recommendation);
    resultCard.appendChild(dashboardLink);

    answerOptions.appendChild(resultCard);

    submitAnswerButton.hidden = true;
    submitAnswerButton.style.display = "none";
}


if (practiceForm) {
    practiceForm.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            hideError();

            if (!practiceAttempt) {
                showError(
                    "The practice session is not available.",
                );
                return;
            }

            const selectedAnswer = document.querySelector(
                'input[name="answer"]:checked',
            );

            if (!selectedAnswer) {
                showError(
                    "Please select an answer before continuing.",
                );
                return;
            }

            const question =
                practiceAttempt.questions[currentQuestionIndex];

            submitAnswerButton.disabled = true;
            submitAnswerButton.textContent = "Submitting...";

            try {
                await submitPracticeAnswer(
                    question.id,
                    selectedAnswer.value,
                );

                currentQuestionIndex += 1;

                if (
                    currentQuestionIndex
                    < practiceAttempt.questions.length
                ) {
                    renderQuestion();
                    return;
                }

                const completion = await completePractice();
                const improvement = await loadImprovement();

                renderPracticeResult(
                    completion,
                    improvement,
                );

            } catch (error) {
                console.error(
                    "Practice answer submission error:",
                    error,
                );

                showError(
                    error.message
                    || "Unable to submit your answer.",
                );

                submitAnswerButton.disabled = false;
                submitAnswerButton.textContent = "Submit answer";
            }
        },
    );
}


if (logoutButton) {
    logoutButton.addEventListener(
        "click",
        redirectToLogin,
    );
}


initializePractice();
