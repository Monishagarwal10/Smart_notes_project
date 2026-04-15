import io
import os
import re
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file

from utils.nlp_utils import (
    check_quiz_answers,
    clean_text,
    extract_keywords,
    generate_quiz_questions,
    generate_mindmap_data,
    normalize_pdf_text,
    segment_content,
    summarize_text,
)
from utils.storage_utils import load_sessions, save_session

try:
    import PyPDF2
except Exception:  # pragma: no cover - graceful fallback if dependency is missing
    PyPDF2 = None

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except Exception:  # pragma: no cover
    canvas = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


def build_response_payload(source_type, source_title, raw_text):
    normalized_raw = normalize_pdf_text(raw_text)
    cleaned = clean_text(raw_text)
    summary = summarize_text(cleaned)
    keywords = extract_keywords(cleaned, top_k=15)
    mindmap = generate_mindmap_data(cleaned, keywords)
    sections = segment_content(normalized_raw)
    return {
        "source_type": source_type,
        "title": source_title or "Untitled Session",
        "raw_text": normalized_raw,
        "cleaned_text": cleaned,
        "summary": summary,
        "keywords": keywords,
        "mindmap": mindmap,
        "sections": sections,
        "processed_at": datetime.now().isoformat(timespec="seconds"),
    }


def extract_pdf_text(file_storage):
    if PyPDF2 is None:
        raise RuntimeError("PyPDF2 is not installed. Please install dependencies first.")

    reader = PyPDF2.PdfReader(file_storage)
    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page": idx, "text": text})

    full_text = "\n".join(page["text"] for page in pages).strip()
    warning = ""
    if not full_text:
        warning = (
            "The PDF appears to contain little or no selectable text. "
            "It may be a scanned document and require OCR."
        )
    return full_text, pages, warning


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/summary")
def summary_page():
    return render_template("summary.html")


@app.route("/mindmap")
def mindmap_page():
    return render_template("mindmap.html")


@app.route("/smart-learning")
def smart_learning_page():
    return render_template("quiz.html")


@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    if "pdf" not in request.files:
        return jsonify({"error": "No PDF file part found in request."}), 400

    pdf_file = request.files["pdf"]
    if not pdf_file or not pdf_file.filename:
        return jsonify({"error": "Please choose a PDF file."}), 400

    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    try:
        raw_text, pages, warning = extract_pdf_text(pdf_file)
        payload = build_response_payload("pdf", pdf_file.filename, raw_text)
        payload["pages"] = pages
        payload["warning"] = warning
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"error": f"Failed to process PDF: {exc}"}), 500


@app.route("/process_text", methods=["POST"])
def process_text():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    title = data.get("title", "Manual Notes")

    if not text:
        return jsonify({"error": "Please provide note text to process."}), 400

    payload = build_response_payload("text", title, text)
    return jsonify(payload)


@app.route("/process_speech", methods=["POST"])
def process_speech():
    data = request.get_json(silent=True) or {}
    transcript = data.get("transcript", "").strip()
    title = data.get("title", "Live Lecture Notes")

    if not transcript:
        return jsonify({"error": "Transcript is empty. Capture some speech first."}), 400

    payload = build_response_payload("speech", title, transcript)
    return jsonify(payload)


@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    data = request.get_json(silent=True) or {}
    text = data.get("text") or data.get("raw_text") or data.get("cleaned_text") or ""
    text = text.strip()
    summary = data.get("summary", {})
    keywords = data.get("keywords", [])
    max_questions = data.get("max_questions", 5)

    try:
        max_questions = int(max_questions)
    except (TypeError, ValueError):
        max_questions = 5
    max_questions = min(max(max_questions, 3), 10)

    if not text and summary:
        text = " ".join(summary.get("key_points", []))

    if not text:
        return jsonify({"error": "No notes content found. Upload/process notes first."}), 400

    questions = generate_quiz_questions(
        text=text,
        summary=summary,
        keywords=keywords,
        max_questions=max_questions,
    )
    if not questions:
        return jsonify({"error": "Not enough content to generate quiz questions."}), 400

    return jsonify({"questions": questions})


@app.route("/check_quiz", methods=["POST"])
def check_quiz():
    data = request.get_json(silent=True) or {}
    questions = data.get("questions", [])
    answers = data.get("answers", {})
    if not questions:
        return jsonify({"error": "No quiz questions provided."}), 400
    if not isinstance(answers, dict):
        return jsonify({"error": "Answers format is invalid."}), 400

    result = check_quiz_answers(questions, answers)
    return jsonify(result)


@app.route("/generate_mindmap", methods=["POST"])
def generate_mindmap():
    data = request.get_json(silent=True) or {}
    section_id = data.get("section_id")
    if section_id and data.get("sections"):
        for section in data["sections"]:
            if section.get("id") == section_id:
                return jsonify({"mindmap": section.get("mindmap", {"nodes": [], "edges": []})})

    text = clean_text(data.get("text", ""))
    keywords = data.get("keywords", [])
    if not text:
        return jsonify({"error": "Text is required to generate mind map."}), 400

    mindmap = generate_mindmap_data(text, keywords)
    return jsonify({"mindmap": mindmap})


@app.route("/save_note", methods=["POST"])
def save_note():
    data = request.get_json(silent=True) or {}
    required_fields = ["title", "raw_text", "summary", "keywords", "mindmap"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    saved = save_session(BASE_DIR, data)
    return jsonify({"message": "Session saved successfully.", "session": saved})


@app.route("/load_notes", methods=["GET"])
def load_notes():
    sessions = load_sessions(BASE_DIR)
    sessions = sorted(sessions, key=lambda item: item.get("saved_at", ""), reverse=True)
    return jsonify({"sessions": sessions})


@app.route("/export", methods=["POST"])
def export_note():
    data = request.get_json(silent=True) or {}
    export_type = data.get("export_type", "full_json")
    title = re.sub(r"[^a-zA-Z0-9_-]+", "_", data.get("title", "smart_note")).strip("_")
    title = title or "smart_note"

    if export_type == "summary_txt":
        summary = data.get("summary", {})
        content = (
            f"{summary.get('title', 'Summary')}\n\n"
            f"{summary.get('paragraph', '')}\n\n"
            "Key Points:\n"
            + "\n".join(f"- {point}" for point in summary.get("key_points", []))
        )
        return send_file(
            io.BytesIO(content.encode("utf-8")),
            as_attachment=True,
            download_name=f"{title}_summary.txt",
            mimetype="text/plain",
        )

    if export_type == "keywords_json":
        return jsonify({"keywords": data.get("keywords", [])})

    if export_type == "summary_pdf":
        if canvas is None:
            return jsonify({"error": "PDF export is unavailable. Install reportlab."}), 400

        summary = data.get("summary", {})
        buffer = io.BytesIO()
        pdf_canvas = canvas.Canvas(buffer, pagesize=letter)
        pdf_canvas.setTitle(f"{title} Summary")
        y_pos = 760

        lines = [summary.get("title", "Summary"), "", summary.get("paragraph", ""), "", "Key Points:"]
        lines.extend([f"- {point}" for point in summary.get("key_points", [])])

        pdf_canvas.setFont("Helvetica", 11)
        for line in lines:
            wrapped = re.findall(r".{1,95}(?:\s+|$)", line) or [""]
            for segment in wrapped:
                if y_pos < 60:
                    pdf_canvas.showPage()
                    pdf_canvas.setFont("Helvetica", 11)
                    y_pos = 760
                pdf_canvas.drawString(40, y_pos, segment.strip())
                y_pos -= 18

        pdf_canvas.save()
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{title}_summary.pdf",
            mimetype="application/pdf",
        )

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)