const state = {
    questions: [],
    checkedResultsById: {},
};

const elements = {
    quizText: document.getElementById("quizText"),
    generateQuiz: document.getElementById("generateQuiz"),
    checkAnswers: document.getElementById("checkAnswers"),
    resetQuiz: document.getElementById("resetQuiz"),
    quizList: document.getElementById("quizList"),
    quizCheckWrap: document.getElementById("quizCheckWrap"),
    toast: document.getElementById("toast"),
};

function showToast(message, isError = false) {
    elements.toast.textContent = message;
    elements.toast.style.background = isError ? "#8b1f2f" : "#1f2e57";
    elements.toast.classList.add("show");
    setTimeout(() => elements.toast.classList.remove("show"), 2200);
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || "Request failed.");
    }
    return data;
}

function loadStoredSession() {
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

function renderQuestions() {
    elements.quizList.innerHTML = "";
    if (!state.questions.length) {
        elements.quizList.innerHTML = "<p class='section-subtitle'>No quiz available. Generate one first.</p>";
        updateCheckButtonVisibility();
        return;
    }

    state.questions.forEach((question, idx) => {
        const block = document.createElement("article");
        block.className = "quiz-card";
        const checked = state.checkedResultsById[question.id];
        const selectedIndex = checked ? checked.selected_index : null;
        const correctIndex = checked ? checked.correct_index : null;

        const options = question.options
            .map((option, optionIndex) => {
                let optionClass = "quiz-option";
                if (checked) {
                    if (optionIndex === correctIndex) {
                        optionClass += " quiz-option-correct";
                    } else if (optionIndex === selectedIndex && selectedIndex !== correctIndex) {
                        optionClass += " quiz-option-wrong";
                    }
                }
                return `
                    <label class="${optionClass}">
                        <input type="radio" name="${question.id}" value="${optionIndex}" ${selectedIndex === optionIndex ? "checked" : ""}>
                        <span>${option}</span>
                    </label>
                `;
            })
            .join("");
        const explanation = checked && !checked.is_correct
            ? `<div class="quiz-explanation">Why incorrect:<br>${String(checked.explanation || "").replaceAll("\n", "<br>")}</div>`
            : "";
        block.innerHTML = `
            <h4>Q${idx + 1}. ${question.question}</h4>
            <div class="quiz-options">${options}</div>
            ${explanation}
        `;
        elements.quizList.appendChild(block);
    });

    bindOptionChangeEvents();
    updateCheckButtonVisibility();
}

function collectAnswers() {
    const answers = {};
    state.questions.forEach((question) => {
        const selected = document.querySelector(`input[name="${question.id}"]:checked`);
        if (selected) {
            answers[question.id] = Number(selected.value);
        }
    });
    return answers;
}

function areAllQuestionsAnswered() {
    const answers = collectAnswers();
    return state.questions.length > 0 && Object.keys(answers).length === state.questions.length;
}

function updateCheckButtonVisibility() {
    if (areAllQuestionsAnswered()) {
        elements.quizCheckWrap.classList.remove("hidden");
        return;
    }
    elements.quizCheckWrap.classList.add("hidden");
}

function bindOptionChangeEvents() {
    state.questions.forEach((question) => {
        const options = document.querySelectorAll(`input[name="${question.id}"]`);
        options.forEach((option) => {
            option.addEventListener("change", () => {
                updateCheckButtonVisibility();
            });
        });
    });
}

async function onGenerateQuiz() {
    const customText = elements.quizText.value.trim();
    const stored = loadStoredSession() || {};
    const payload = {
        text: customText || stored.raw_text || stored.cleaned_text || "",
        summary: stored.summary || {},
        keywords: stored.keywords || [],
        max_questions: 5,
    };

    if (!payload.text && !(payload.summary.key_points || []).length) {
        showToast("Process notes on Home page or paste notes here first.", true);
        return;
    }

    try {
        const data = await fetchJson("/generate_quiz", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        state.questions = data.questions || [];
        state.checkedResultsById = {};
        renderQuestions();
        showToast("Quiz generated successfully.");
    } catch (error) {
        showToast(error.message, true);
    }
}

async function onCheckAnswers() {
    if (!state.questions.length) {
        showToast("Generate a quiz first.", true);
        return;
    }
    const answers = collectAnswers();
    if (Object.keys(answers).length !== state.questions.length) {
        showToast("Please answer all questions first.", true);
        return;
    }
    try {
        const result = await fetchJson("/check_quiz", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ questions: state.questions, answers }),
        });
        state.checkedResultsById = {};
        (result.results || []).forEach((item) => {
            state.checkedResultsById[item.id] = item;
        });
        renderQuestions();
        showToast("Answers checked.");
    } catch (error) {
        showToast(error.message, true);
    }
}

function onResetQuiz() {
    state.questions = [];
    state.checkedResultsById = {};
    elements.quizText.value = "";
    renderQuestions();
}

elements.generateQuiz.addEventListener("click", onGenerateQuiz);
elements.checkAnswers.addEventListener("click", onCheckAnswers);
elements.resetQuiz.addEventListener("click", onResetQuiz);
