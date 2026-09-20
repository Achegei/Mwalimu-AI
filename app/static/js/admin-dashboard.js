const accessToken = localStorage.getItem(
    "mwalimu_access_token",
);

const adminName = document.getElementById(
    "admin-name",
);

const logoutButton = document.getElementById(
    "logout-button",
);

const dashboardError = document.getElementById(
    "admin-dashboard-error",
);

const dashboardLoading = document.getElementById(
    "admin-dashboard-loading",
);

const dashboardMain = document.getElementById(
    "admin-dashboard-main",
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
        let message = "Unable to load administration data.";

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

    if (user.role !== "admin") {
        redirectToLogin();
        return null;
    }

    localStorage.setItem(
        "mwalimu_user",
        JSON.stringify(user),
    );

    if (adminName) {
        adminName.textContent = user.full_name;
    }

    return user;
}


async function initializeDashboard() {
    if (!accessToken) {
        redirectToLogin();
        return;
    }

    setDashboardLoading(true);

    try {
        const user = await loadCurrentUser();

        if (!user) {
            return;
        }

        setDashboardLoading(false);

    } catch (error) {
        console.error(
            "Admin dashboard error:",
            error,
        );

        setDashboardLoading(false);

        showDashboardError(
            error.message
            || "Unable to load the administration workspace.",
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


// -----------------------------------------------------------------------------
// Document library
// -----------------------------------------------------------------------------

const loadDocumentsButton = document.getElementById(
    "load-documents-button",
);

const documentListPanel = document.getElementById(
    "document-list-panel",
);

const documentListBody = document.getElementById(
    "document-list-body",
);

const documentListContent = document.getElementById(
    "document-list-content",
);

const documentListLoading = document.getElementById(
    "document-list-loading",
);

const documentListEmpty = document.getElementById(
    "document-list-empty",
);

const documentListError = document.getElementById(
    "document-list-error",
);

const closeDocumentListButton = document.getElementById(
    "close-document-list",
);


const uploadDocumentButton = document.getElementById(
    "upload-document-button",
);

const uploadPanel = document.getElementById(
    "document-upload-panel",
);

const uploadForm = document.getElementById(
    "document-upload-form",
);

const cancelUploadButton = document.getElementById(
    "cancel-document-upload",
);

const formLevelSelect = document.getElementById(
    "document-form-level",
);

const subjectSelect = document.getElementById(
    "document-subject",
);

const topicSelect = document.getElementById(
    "document-topic",
);

const documentTypeSelect = document.getElementById(
    "document-type",
);

const examFields = document.getElementById(
    "document-exam-fields",
);

const uploadError = document.getElementById(
    "document-upload-error",
);

const uploadSuccess = document.getElementById(
    "document-upload-success",
);

const submitUploadButton = document.getElementById(
    "submit-document-upload",
);


function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatDocumentType(value) {
    if (!value) {
        return "—";
    }

    return value
        .split("_")
        .map(
            (part) => (
                part.charAt(0).toUpperCase()
                + part.slice(1)
            ),
        )
        .join(" ");
}


function formatProcessingStatus(value) {
    if (!value) {
        return "Unknown";
    }

    return value
        .split("_")
        .map(
            (part) => (
                part.charAt(0).toUpperCase()
                + part.slice(1)
            ),
        )
        .join(" ");
}


function resetDocumentListState() {
    if (documentListError) {
        documentListError.hidden = true;
        documentListError.textContent = "";
    }

    if (documentListLoading) {
        documentListLoading.hidden = true;
    }

    if (documentListEmpty) {
        documentListEmpty.hidden = true;
    }

    if (documentListContent) {
        documentListContent.hidden = true;
    }
}


function renderDocuments(documents) {
    if (!documentListBody) {
        return;
    }

    documentListBody.innerHTML = "";

    if (!Array.isArray(documents) || documents.length === 0) {
        if (documentListEmpty) {
            documentListEmpty.hidden = false;
        }

        return;
    }

    for (const documentItem of documents) {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>
                <strong>
                    ${escapeHtml(documentItem.title)}
                </strong>
            </td>

            <td>
                ${escapeHtml(
                    formatDocumentType(
                        documentItem.document_type,
                    ),
                )}
            </td>

            <td>
                Form ${escapeHtml(documentItem.form_level)}
            </td>

            <td>
                ${escapeHtml(documentItem.original_filename)}
            </td>

            <td>
                ${escapeHtml(
                    formatProcessingStatus(
                        documentItem.processing_status,
                    ),
                )}
            </td>
        `;

        documentListBody.appendChild(row);
    }

    if (documentListContent) {
        documentListContent.hidden = false;
    }
}


async function loadDocuments() {
    if (!documentListPanel) {
        return;
    }

    resetDocumentListState();

    documentListPanel.hidden = false;

    if (documentListLoading) {
        documentListLoading.hidden = false;
    }

    try {
        const documents = await apiRequest(
            "/admin/documents",
        );

        if (!documents) {
            return;
        }

        if (documentListLoading) {
            documentListLoading.hidden = true;
        }

        renderDocuments(documents);

        documentListPanel.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });

    } catch (error) {
        console.error(
            "Document list error:",
            error,
        );

        if (documentListLoading) {
            documentListLoading.hidden = true;
        }

        if (documentListError) {
            documentListError.textContent = (
                error.message
                || "Unable to load school documents."
            );

            documentListError.hidden = false;
        }
    }
}


function hideUploadMessages() {
    if (uploadError) {
        uploadError.hidden = true;
        uploadError.textContent = "";
    }

    if (uploadSuccess) {
        uploadSuccess.hidden = true;
        uploadSuccess.textContent = "";
    }
}


function showUploadError(message) {
    if (!uploadError) {
        return;
    }

    uploadError.textContent = message;
    uploadError.hidden = false;
}


function showUploadSuccess(message) {
    if (!uploadSuccess) {
        return;
    }

    uploadSuccess.textContent = message;
    uploadSuccess.hidden = false;
}


function resetSubjectSelect() {
    if (!subjectSelect) {
        return;
    }

    subjectSelect.innerHTML = `
        <option value="">
            Select form level first
        </option>
    `;

    subjectSelect.disabled = true;
}


function resetTopicSelect(message = "Select subject first") {
    if (!topicSelect) {
        return;
    }

    topicSelect.innerHTML = `
        <option value="">
            ${message}
        </option>
    `;

    topicSelect.disabled = true;
}


async function adminApiRequest(
    url,
    options = {},
) {
    const headers = new Headers(
        options.headers || {},
    );

    headers.set(
        "Authorization",
        `Bearer ${accessToken}`,
    );

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

    if (!response.ok) {
        let message = "The request could not be completed.";

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


async function loadSubjects() {
    if (!subjectSelect) {
        return;
    }

    subjectSelect.disabled = true;

    subjectSelect.innerHTML = `
        <option value="">
            Loading subjects...
        </option>
    `;

    resetTopicSelect();

    try {
        const subjects = await adminApiRequest(
            "/admin/subjects",
        );

        if (!subjects) {
            return;
        }

        subjectSelect.innerHTML = `
            <option value="">
                Select subject
            </option>
        `;

        for (const subject of subjects) {
            const option = document.createElement(
                "option",
            );

            option.value = subject.id;
            option.textContent = subject.name;

            subjectSelect.appendChild(option);
        }

        subjectSelect.disabled = false;

    } catch (error) {
        console.error(
            "Unable to load subjects:",
            error,
        );

        resetSubjectSelect();

        showUploadError(
            error.message
            || "Unable to load subjects.",
        );
    }
}


async function loadTopics() {
    if (
        !subjectSelect
        || !formLevelSelect
        || !topicSelect
    ) {
        return;
    }

    const subjectId = subjectSelect.value;
    const formLevel = formLevelSelect.value;

    if (!subjectId || !formLevel) {
        resetTopicSelect();
        return;
    }

    topicSelect.disabled = true;

    topicSelect.innerHTML = `
        <option value="">
            Loading topics...
        </option>
    `;

    try {
        const subject = await adminApiRequest(
            `/admin/subjects/${subjectId}/topics`
            + `?form_level=${formLevel}`,
        );

        if (!subject) {
            return;
        }

        topicSelect.innerHTML = `
            <option value="">
                No specific topic
            </option>
        `;

        for (const topic of subject.topics) {
            const option = document.createElement(
                "option",
            );

            option.value = topic.id;
            option.textContent = topic.title;

            topicSelect.appendChild(option);
        }

        topicSelect.disabled = false;

    } catch (error) {
        console.error(
            "Unable to load topics:",
            error,
        );

        resetTopicSelect(
            "Unable to load topics",
        );

        showUploadError(
            error.message
            || "Unable to load topics.",
        );
    }
}


function updateExamFields() {
    if (
        !documentTypeSelect
        || !examFields
    ) {
        return;
    }

    const examTypes = new Set([
        "past_paper",
        "marking_scheme",
        "mock_exam",
    ]);

    const isExamDocument = examTypes.has(
        documentTypeSelect.value,
    );

    examFields.hidden = !isExamDocument;

    if (!isExamDocument) {
        const examYearInput = document.getElementById(
            "document-exam-year",
        );

        const paperNumberInput = document.getElementById(
            "document-paper-number",
        );

        if (examYearInput) {
            examYearInput.value = "";
        }

        if (paperNumberInput) {
            paperNumberInput.value = "";
        }
    }
}


async function submitDocument(event) {
    event.preventDefault();

    if (!uploadForm) {
        return;
    }

    hideUploadMessages();

    const formData = new FormData(uploadForm);

    if (!formData.get("topic_id")) {
        formData.delete("topic_id");
    }

    if (!formData.get("exam_year")) {
        formData.delete("exam_year");
    }

    if (!formData.get("paper_number")) {
        formData.delete("paper_number");
    }

    if (submitUploadButton) {
        submitUploadButton.disabled = true;
        submitUploadButton.textContent = (
            "Uploading and processing..."
        );
    }

    try {
        const documentData = await adminApiRequest(
            "/admin/documents",
            {
                method: "POST",
                body: formData,
            },
        );

        if (!documentData) {
            return;
        }

        showUploadSuccess(
            `Document "${documentData.title}" uploaded successfully. `
            + `Processing status: ${documentData.processing_status}.`,
        );

        uploadForm.reset();

        resetSubjectSelect();
        resetTopicSelect();
        updateExamFields();

    } catch (error) {
        console.error(
            "Document upload failed:",
            error,
        );

        showUploadError(
            error.message
            || "Unable to upload the document.",
        );

    } finally {
        if (submitUploadButton) {
            submitUploadButton.disabled = false;
            submitUploadButton.textContent = (
                "Upload and process"
            );
        }
    }
}


if (loadDocumentsButton) {
    loadDocumentsButton.addEventListener(
        "click",
        loadDocuments,
    );
}


if (closeDocumentListButton) {
    closeDocumentListButton.addEventListener(
        "click",
        () => {
            if (documentListPanel) {
                documentListPanel.hidden = true;
            }

            resetDocumentListState();
        },
    );
}


if (uploadDocumentButton) {
    uploadDocumentButton.addEventListener(
        "click",
        async () => {
            hideUploadMessages();

            if (uploadPanel) {
                uploadPanel.hidden = false;

                uploadPanel.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                });
            }

            if (
                formLevelSelect
                && formLevelSelect.value
            ) {
                await loadSubjects();
            }
        },
    );
}


if (cancelUploadButton) {
    cancelUploadButton.addEventListener(
        "click",
        () => {
            if (uploadPanel) {
                uploadPanel.hidden = true;
            }

            hideUploadMessages();
        },
    );
}


if (formLevelSelect) {
    formLevelSelect.addEventListener(
        "change",
        async () => {
            hideUploadMessages();

            resetTopicSelect();

            if (!formLevelSelect.value) {
                resetSubjectSelect();
                return;
            }

            await loadSubjects();
        },
    );
}


if (subjectSelect) {
    subjectSelect.addEventListener(
        "change",
        async () => {
            hideUploadMessages();
            await loadTopics();
        },
    );
}


if (documentTypeSelect) {
    documentTypeSelect.addEventListener(
        "change",
        updateExamFields,
    );
}


if (uploadForm) {
    uploadForm.addEventListener(
        "submit",
        submitDocument,
    );
}


updateExamFields();
