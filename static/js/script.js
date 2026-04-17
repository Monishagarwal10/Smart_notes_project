const state = {
    currentResult: null,
    recognition: null,
    lecture: {
        finalTranscript: "",
        interimTranscript: "",
        status: "stopped",
        shouldRestart: false,
        isStopping: false,
    },
};

const elements = {
    navMenu: document.getElementById("navMenu"),
    menuToggle: document.getElementById("menuToggle"),
    pdfForm: document.getElementById("pdfForm"),
    pdfFile: document.getElementById("pdfFile"),
    pdfWarning: document.getElementById("pdfWarning"),
    manualTitle: document.getElementById("manualTitle"),
    manualText: document.getElementById("manualText"),
    processText: document.getElementById("processText"),
    startSpeech: document.getElementById("startSpeech"),
    pauseSpeech: document.getElementById("pauseSpeech"),
    processSpeech: document.getElementById("processSpeech"),
    speechTranscript: document.getElementById("speechTranscript"),
    lectureStatus: document.getElementById("lectureStatus"),
    lectureRecordingDot: document.getElementById("lectureRecordingDot"),
    summaryTitle: document.getElementById("summaryTitle"),
    summaryMeta: document.getElementById("summaryMeta"),
    summaryParagraph: document.getElementById("summaryParagraph"),
    summaryPoints: document.getElementById("summaryPoints"),
    keywordChips: document.getElementById("keywordChips"),
    saveSession: document.getElementById("saveSession"),
    refreshSessions: document.getElementById("refreshSessions"),
    sessionList: document.getElementById("sessionList"),
    exportSummaryTxt: document.getElementById("exportSummaryTxt"),
    exportSummaryPdf: document.getElementById("exportSummaryPdf"),
    exportKeywords: document.getElementById("exportKeywords"),
    exportFull: document.getElementById("exportFull"),
    exportMindmapPng: document.getElementById("exportMindmapPng"),
    toast: document.getElementById("toast"),
};

function showToast(message, isError = false) {
    if (!elements.toast) return;
    elements.toast.textContent = message;
    elements.toast.style.background = isError ? "#8b1f2f" : "#1f2e57";
    elements.toast.classList.add("show");
    setTimeout(() => elements.toast.classList.remove("show"), 2200);
}

function onClick(element, handler) {
    if (element) element.addEventListener("click", handler);
}

function onSubmit(element, handler) {
    if (element) element.addEventListener("submit", handler);
}

function setCurrentResult(data) {
    state.currentResult = data;
    localStorage.setItem("smartNoteCurrentResult", JSON.stringify(data));
    renderSummary(data.summary || {});
    renderKeywords(data.keywords || []);
}

function renderSummary(summary) {
    if (!elements.summaryTitle || !elements.summaryParagraph || !elements.summaryPoints || !elements.summaryMeta) return;

    elements.summaryTitle.textContent = summary.title || "Summary";
    elements.summaryParagraph.textContent = summary.paragraph || "No summary generated.";

    const points = summary.key_points || [];
    elements.summaryMeta.textContent = `${points.length} key points`;
    elements.summaryPoints.innerHTML = "";

    points.forEach((point, idx) => {
        const item = document.createElement("div");
        item.className = "keypoint-item";
        item.innerHTML = `<strong>Point ${idx + 1}:</strong> ${point}`;
        elements.summaryPoints.appendChild(item);
    });
}

function renderKeywords(keywords) {
    if (!elements.keywordChips) return;

    elements.keywordChips.innerHTML = "";
    keywords.forEach((keyword) => {
        const chip = document.createElement("span");
        chip.className = "chip";
        chip.textContent = `${keyword.term} (${keyword.score})`;
        elements.keywordChips.appendChild(chip);
    });
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    let data = {};
    try {
        data = await response.json();
    } catch {}

    if (!response.ok) throw new Error(data.error || "Request failed.");
    return data;
}

function triggerDownload(filename, blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

onClick(elements.menuToggle, () => {
    if (elements.navMenu) elements.navMenu.classList.toggle("open");
});

onSubmit(elements.pdfForm, async (event) => {
    event.preventDefault();

    const file = elements.pdfFile.files[0];
    if (!file) {
        showToast("Please select a PDF file first.", true);
        return;
    }

    const formData = new FormData();
    formData.append("pdf", file);

    try {
        const result = await fetchJson("/upload_pdf", { method: "POST", body: formData });
        elements.pdfWarning.textContent = result.warning || "";
        setCurrentResult(result);

        showToast("PDF processed. Redirecting to Summary page.");
        setTimeout(() => window.location.href = "/summary", 550);
    } catch (error) {
        showToast(error.message, true);
    }
});

onClick(elements.processText, async () => {
    const text = elements.manualText.value.trim();

    if (!text) {
        showToast("Enter notes before processing.", true);
        return;
    }

    try {
        const result = await fetchJson("/process_text", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: elements.manualTitle.value.trim() || "Manual Notes",
                text,
            }),
        });

        setCurrentResult(result);
        showToast("Manual notes processed. Redirecting to Summary page.");
        setTimeout(() => window.location.href = "/summary", 550);
    } catch (error) {
        showToast(error.message, true);
    }
});

/* ------------------ SAVED NOTES FIX ------------------ */

onClick(elements.saveSession, () => {
    if (!state.currentResult) {
        showToast("Process notes before saving.", true);
        return;
    }

    let savedNotes = JSON.parse(localStorage.getItem("myNotes")) || [];

    const sessionToSave = {
        ...state.currentResult,
        saved_at: new Date().toLocaleString()
    };

    savedNotes.push(sessionToSave);
    localStorage.setItem("myNotes", JSON.stringify(savedNotes));

    showToast("Session saved locally.");
    loadSessions();
});

function loadSessions() {
    const sessions = JSON.parse(localStorage.getItem("myNotes")) || [];

    elements.sessionList.innerHTML = "";

    if (!sessions.length) {
        elements.sessionList.innerHTML = "<p class='section-subtitle'>No saved sessions yet.</p>";
        return;
    }

    sessions.forEach((session) => {
        const row = document.createElement("article");
        row.className = "session-item";

        row.innerHTML = `
            <div>
                <strong>${session.title}</strong>
                <div class="session-meta">${session.source_type || "local"} • ${session.saved_at}</div>
            </div>
        `;

        const button = document.createElement("button");
        button.className = "btn btn-outline";
        button.textContent = "Load";

        button.addEventListener("click", () => {
            setCurrentResult(session);
            showToast(`Loaded session: ${session.title}`);
        });

        row.appendChild(button);
        elements.sessionList.appendChild(row);
    });
}

onClick(elements.refreshSessions, loadSessions);

/* ------------------ END FIX ------------------ */

if (elements.lectureStatus) {
    elements.lectureStatus.textContent = "Stopped";
}

if (elements.sessionList) {
    loadSessions();
}