const state = {
    currentResult: null,
    recognition: null,
    speechBuffer: "",
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
    stopSpeech: document.getElementById("stopSpeech"),
    processSpeech: document.getElementById("processSpeech"),
    speechTranscript: document.getElementById("speechTranscript"),
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
    elements.toast.textContent = message;
    elements.toast.style.background = isError ? "#8b1f2f" : "#1f2e57";
    elements.toast.classList.add("show");
    setTimeout(() => elements.toast.classList.remove("show"), 2200);
}

function setCurrentResult(data) {
    state.currentResult = data;
    localStorage.setItem("smartNoteCurrentResult", JSON.stringify(data));
    renderSummary(data.summary || {});
    renderKeywords(data.keywords || []);
}

function renderSummary(summary) {
    if (!elements.summaryTitle || !elements.summaryParagraph || !elements.summaryPoints || !elements.summaryMeta) {
        return;
    }
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
    if (!elements.keywordChips) {
        return;
    }
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
    } catch (error) {
        data = {};
    }
    if (!response.ok) {
        throw new Error(data.error || "Request failed.");
    }
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

elements.menuToggle.addEventListener("click", () => {
    if (elements.navMenu) {
        elements.navMenu.classList.toggle("open");
    }
});

elements.pdfForm.addEventListener("submit", async (event) => {
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
        setTimeout(() => {
            window.location.href = "/summary";
        }, 550);
    } catch (error) {
        showToast(error.message, true);
    }
});

elements.processText.addEventListener("click", async () => {
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
        setTimeout(() => {
            window.location.href = "/summary";
        }, 550);
    } catch (error) {
        showToast(error.message, true);
    }
});

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast("Web Speech API is not supported in this browser.", true);
        return;
    }
    state.recognition = new SpeechRecognition();
    state.recognition.continuous = true;
    state.recognition.interimResults = true;
    state.recognition.lang = "en-US";

    state.recognition.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
            transcript += event.results[i][0].transcript + " ";
        }
        state.speechBuffer = `${state.speechBuffer} ${transcript}`.trim();
        elements.speechTranscript.value = state.speechBuffer;
    };

    state.recognition.onerror = () => {
        showToast("Speech recognition encountered an issue.", true);
    };
}

elements.startSpeech.addEventListener("click", () => {
    if (!state.recognition) {
        initSpeechRecognition();
    }
    if (state.recognition) {
        state.recognition.start();
        showToast("Live lecture capture started.");
    }
});

elements.stopSpeech.addEventListener("click", () => {
    if (state.recognition) {
        state.recognition.stop();
        showToast("Capture stopped.");
    }
});

elements.processSpeech.addEventListener("click", async () => {
    const transcript = elements.speechTranscript.value.trim();
    if (!transcript) {
        showToast("No transcript captured yet.", true);
        return;
    }
    try {
        const result = await fetchJson("/process_speech", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: "Live Lecture Session",
                transcript,
            }),
        });
        setCurrentResult(result);
        showToast("Transcript processed. Redirecting to Summary page.");
        setTimeout(() => {
            window.location.href = "/summary";
        }, 550);
    } catch (error) {
        showToast(error.message, true);
    }
});

elements.saveSession.addEventListener("click", async () => {
    if (!state.currentResult) {
        showToast("Process notes before saving.", true);
        return;
    }
    try {
        await fetchJson("/save_note", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(state.currentResult),
        });
        showToast("Session saved.");
        await loadSessions();
    } catch (error) {
        showToast(error.message, true);
    }
});

async function loadSessions() {
    try {
        const data = await fetchJson("/load_notes");
        elements.sessionList.innerHTML = "";
        const sessions = data.sessions || [];
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
                    <div class="session-meta">${session.source_type} • ${session.saved_at}</div>
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
    } catch (error) {
        showToast(error.message, true);
    }
}

elements.refreshSessions.addEventListener("click", loadSessions);

async function exportViaBackend(exportType, fallbackFilename) {
    if (!state.currentResult) {
        showToast("Process or load a session first.", true);
        return;
    }
    try {
        const response = await fetch("/export", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                ...state.currentResult,
                export_type: exportType,
                title: state.currentResult.title || "smart_note",
            }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || "Export failed.");
        }

        if (exportType === "keywords_json") {
            const json = await response.json();
            const blob = new Blob([JSON.stringify(json, null, 2)], { type: "application/json" });
            triggerDownload(fallbackFilename, blob);
        } else if (exportType === "full_json") {
            const json = await response.json();
            const blob = new Blob([JSON.stringify(json, null, 2)], { type: "application/json" });
            triggerDownload(fallbackFilename, blob);
        } else {
            const blob = await response.blob();
            triggerDownload(fallbackFilename, blob);
        }
        showToast("Export ready.");
    } catch (error) {
        showToast(error.message, true);
    }
}

elements.exportSummaryTxt.addEventListener("click", () => exportViaBackend("summary_txt", "summary.txt"));
elements.exportSummaryPdf.addEventListener("click", () => exportViaBackend("summary_pdf", "summary.pdf"));
elements.exportKeywords.addEventListener("click", () => exportViaBackend("keywords_json", "keywords.json"));
elements.exportFull.addEventListener("click", () => exportViaBackend("full_json", "note_package.json"));
elements.exportMindmapPng.addEventListener("click", () => {
    showToast("Use Mind Map page to export the focused map.");
});

loadSessions();