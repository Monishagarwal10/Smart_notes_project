const state = {
    payload: null,
    network: null,
    fullscreen: false,
};

const elements = {
    sectionSelect: document.getElementById("mindmapSectionSelect"),
    renderSelectedMap: document.getElementById("renderSelectedMap"),
    renderWholeMap: document.getElementById("renderWholeMap"),
    toggleFullscreen: document.getElementById("toggleFullscreen"),
    minimizeOverlayBtn: document.getElementById("minimizeOverlayBtn"),
    canvas: document.getElementById("mindmapCanvas"),
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

function buildOptions() {
    return {
        autoResize: true,
        layout: {},
        physics: {
            enabled: false,
        },
        nodes: {
            shape: "box",
            borderWidth: 2,
            margin: { top: 10, right: 12, bottom: 10, left: 12 },
            widthConstraint: { minimum: 220, maximum: 270 },
            font: { face: "Inter", size: 14, color: "#1f2f51", multi: true },
            color: { background: "#ecf2ff", border: "#8ca5e8" },
            shadow: {
                enabled: true,
                color: "rgba(31, 47, 81, 0.18)",
                size: 12,
                x: 0,
                y: 4,
            },
        },
        edges: {
            smooth: { enabled: true, type: "dynamic" },
            arrows: { to: { enabled: true, scaleFactor: 0.7 } },
            color: "#6f7f9f",
            width: 1.8,
        },
        groups: {
            topic: {
                color: { background: "#ffffff", border: "#24345c" },
                font: { color: "#151a28", size: 36, bold: true },
                shape: "text",
                widthConstraint: false,
            },
            theme: { borderWidth: 2 },
        },
        interaction: { dragNodes: true, dragView: true, zoomView: true, hover: true },
    };
}

function renderMap(mindmap) {
    if (!window.vis || !elements.canvas) {
        return;
    }
    if (state.network) {
        state.network.destroy();
    }
    state.network = new vis.Network(
        elements.canvas,
        {
            nodes: new vis.DataSet(mindmap?.nodes || []),
            edges: new vis.DataSet(mindmap?.edges || []),
        },
        buildOptions()
    );
    state.network.once("stabilizationIterationsDone", () => state.network.fit({ animation: true }));
}

function populateSections() {
    const sections = state.payload?.sections || [];
    elements.sectionSelect.innerHTML = "";
    sections.forEach((section) => {
        const option = document.createElement("option");
        option.value = section.id;
        option.textContent = `${section.title} (${section.type})`;
        elements.sectionSelect.appendChild(option);
    });
}

function setFullscreen(enabled) {
    state.fullscreen = enabled;
    document.body.classList.toggle("map-fullscreen", enabled);
    elements.toggleFullscreen.textContent = enabled ? "Minimize" : "Maximize";
    if (state.network) {
        setTimeout(() => state.network.fit({ animation: true }), 140);
    }
}

elements.renderSelectedMap.addEventListener("click", () => {
    const sectionId = elements.sectionSelect.value;
    const section = (state.payload?.sections || []).find((item) => item.id === sectionId);
    if (section) {
        renderMap(section.mindmap);
    }
});

elements.renderWholeMap.addEventListener("click", () => {
    if (state.payload) {
        renderMap(state.payload.mindmap);
    }
});

elements.toggleFullscreen.addEventListener("click", () => {
    setFullscreen(!state.fullscreen);
});

elements.minimizeOverlayBtn.addEventListener("click", () => {
    setFullscreen(false);
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.fullscreen) {
        setFullscreen(false);
    }
});

elements.canvas.addEventListener("dblclick", () => {
    if (!state.fullscreen) {
        setFullscreen(true);
    }
});

function init() {
    state.payload = loadPayload();
    if (!state.payload) {
        return;
    }
    populateSections();
    renderMap(state.payload.mindmap);
}

init();
