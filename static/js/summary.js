const state = {
    payload: null,
    filteredSections: [],
    activeFilter: "all",
};

const elements = {
    sectionSelect: document.getElementById("sectionSelect"),
    summaryTitle: document.getElementById("summaryTitle"),
    summaryParagraph: document.getElementById("summaryParagraph"),
    summaryPoints: document.getElementById("summaryPoints"),
    keywordChips: document.getElementById("keywordChips"),
    viewWhole: document.getElementById("viewWhole"),
    filterButtons: Array.from(document.querySelectorAll(".filter-btn")),
};

function loadPayload() {
    const raw = localStorage.getItem("smartNoteCurrentResult");
    if (!raw) {
        return null;
    }
    try {
        return JSON.parse(raw);
    } catch (error) {
        return null;
    }
}

function renderSummary(summary) {
    elements.summaryTitle.textContent = summary?.title || "Summary unavailable";
    elements.summaryParagraph.textContent = summary?.paragraph || "No summary found.";
    elements.summaryPoints.innerHTML = "";
    (summary?.key_points || []).forEach((point, idx) => {
        const item = document.createElement("div");
        item.className = "keypoint-item";
        item.innerHTML = `<strong>Point ${idx + 1}:</strong> ${point}`;
        elements.summaryPoints.appendChild(item);
    });
}

function renderKeywords(keywords) {
    elements.keywordChips.innerHTML = "";
    (keywords || []).forEach((keyword) => {
        const chip = document.createElement("span");
        chip.className = "chip";
        chip.textContent = `${keyword.term} (${keyword.score})`;
        elements.keywordChips.appendChild(chip);
    });
}

function applyFilter(filterType) {
    state.activeFilter = filterType;
    elements.filterButtons.forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.filter === filterType);
    });

    const sections = state.payload?.sections || [];
    state.filteredSections = filterType === "all"
        ? sections
        : sections.filter((section) => section.type === filterType);

    elements.sectionSelect.innerHTML = "";
    state.filteredSections.forEach((section) => {
        const option = document.createElement("option");
        option.value = section.id;
        option.textContent = `${section.title} (${section.type})`;
        elements.sectionSelect.appendChild(option);
    });

    if (state.filteredSections.length > 0) {
        renderSection(state.filteredSections[0].id);
    } else {
        renderSummary({ title: "No sections in this filter", paragraph: "", key_points: [] });
        renderKeywords([]);
    }
}

function renderSection(sectionId) {
    const section = (state.payload?.sections || []).find((item) => item.id === sectionId);
    if (!section) {
        return;
    }
    renderSummary(section.summary);
    renderKeywords(section.keywords);
}

elements.sectionSelect.addEventListener("change", (event) => {
    renderSection(event.target.value);
});

elements.viewWhole.addEventListener("click", () => {
    if (!state.payload) {
        return;
    }
    renderSummary(state.payload.summary);
    renderKeywords(state.payload.keywords);
});

elements.filterButtons.forEach((button) => {
    button.addEventListener("click", () => applyFilter(button.dataset.filter));
});

function init() {
    state.payload = loadPayload();
    if (!state.payload) {
        renderSummary({ title: "No processed document found", paragraph: "Go back to home and process a document first.", key_points: [] });
        return;
    }
    renderSummary(state.payload.summary);
    renderKeywords(state.payload.keywords);
    applyFilter("all");
}

init();
