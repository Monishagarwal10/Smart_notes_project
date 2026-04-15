import math
import re
import unicodedata
from collections import Counter


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by", "can",
    "could", "did", "do", "does", "for", "from", "had", "has", "have", "he", "her",
    "here", "him", "his", "how", "i", "if", "in", "into", "is", "it", "its", "just",
    "me", "more", "most", "my", "no", "not", "of", "on", "or", "our", "out", "she",
    "so", "that", "the", "their", "them", "there", "they", "this", "to", "too", "up",
    "us", "was", "we", "were", "what", "when", "where", "which", "who", "why", "will",
    "with", "you", "your", "um", "uh", "like", "okay", "yeah", "basically", "actually",
}


BROKEN_GLYPH_MAP = {
    "Ɵ": "ti",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "’": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "\u00a0": " ",
}


def normalize_pdf_text(text):
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    for bad, good in BROKEN_GLYPH_MAP.items():
        normalized = normalized.replace(bad, good)

    # Common OCR/PDF extraction artifacts where "ti" is broken in words.
    normalized = re.sub(r"([A-Za-z])Ɵ([A-Za-z])", r"\1ti\2", normalized)
    normalized = re.sub(r"([A-Za-z])\s{0,1}\|\s{0,1}([A-Za-z])", r"\1\2", normalized)
    normalized = fix_split_words(normalized)
    return normalized


def fix_split_words(text):
    if not text:
        return ""
    suffixes = (
        "tion", "sion", "ment", "ness", "ing", "ance", "ence", "ology", "ality",
        "ative", "fully", "graphy", "scope", "proof", "logic", "system", "theory",
    )
    pattern = r"\b([A-Za-z]{3,})\s+(" + "|".join(suffixes) + r")\b"
    text = re.sub(pattern, r"\1\2", text, flags=re.IGNORECASE)
    return text


def clean_text(text):
    if not text:
        return ""
    text = normalize_pdf_text(text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[^\w\s\.\,\-\:\;\(\)]", " ", text)
    text = re.sub(r"\b(page|chapter)\s+\d+\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+\n", "\n", text).strip()
    text = fix_split_words(text)
    return text


def split_sentences(text):
    text = clean_text(text)
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def tokenize(text):
    return re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower())


def _score_sentences(sentences, word_scores):
    sentence_scores = []
    for sentence in sentences:
        tokens = tokenize(sentence)
        if not tokens:
            continue
        score = sum(word_scores.get(token, 0.0) for token in tokens) / len(tokens)
        sentence_scores.append((sentence, score))
    return sentence_scores


def summarize_text(text, max_sentences=5):
    sentences = split_sentences(text)
    if not sentences:
        return {"title": "Summary", "paragraph": "", "key_points": []}

    words = [token for token in tokenize(text) if token not in STOPWORDS]
    frequencies = Counter(words)
    if not frequencies:
        top_sentences = sentences[: min(3, len(sentences))]
    else:
        max_freq = max(frequencies.values())
        norm_scores = {word: score / max_freq for word, score in frequencies.items()}
        scored = _score_sentences(sentences, norm_scores)
        # Slightly boost definition-heavy and action-oriented sentences.
        boosted = []
        for sentence, score in scored:
            lower = sentence.lower()
            if any(token in lower for token in ("is defined as", "refers to", "therefore", "important", "key", "because")):
                score += 0.08
            if len(sentence.split()) >= 10:
                score += 0.04
            boosted.append((sentence, score))
        scored = boosted
        scored.sort(key=lambda item: item[1], reverse=True)
        top_sentences = [item[0] for item in scored[:max_sentences]]
        top_sentences.sort(key=lambda sentence: sentences.index(sentence))

    paragraph = " ".join(top_sentences[:3]).strip()
    title_terms = [word.title() for word, _ in frequencies.most_common(3)] if frequencies else ["Smart", "Notes"]
    summary_title = " • ".join(title_terms)
    key_points = top_sentences[:5]
    return {
        "title": summary_title,
        "paragraph": paragraph,
        "key_points": key_points,
    }


def extract_keywords(text, top_k=15):
    tokens = [token for token in tokenize(text) if token not in STOPWORDS]
    if not tokens:
        return []

    doc_len = len(tokens)
    counts = Counter(tokens)
    unique_terms = len(counts) or 1
    keywords = []

    # Simple explainable TF-IDF-like weighting (IDF proxy by uniqueness).
    for term, tf in counts.items():
        tf_score = tf / doc_len
        idf_proxy = math.log((1 + unique_terms) / (1 + tf)) + 1
        score = round(tf_score * idf_proxy * 100, 4)
        keywords.append({"term": term, "score": score})

    keywords.sort(key=lambda item: item["score"], reverse=True)
    return keywords[:top_k]


def _compact_phrase(sentence, max_words=5):
    words = [token for token in tokenize(sentence) if token not in STOPWORDS]
    if not words:
        return "Key Idea"
    return " ".join(words[:max_words]).title()


def _short_description(sentence, max_words=18):
    words = sentence.split()
    trimmed = " ".join(words[:max_words]).strip()
    return trimmed + ("..." if len(words) > max_words else "")


def generate_mindmap_data(text, keywords):
    summary = summarize_text(text, max_sentences=6)
    center_topic = summary["title"].replace(" • ", " | ") if summary["title"] else "Core Topic"
    center_title = f"Mind Map\n{center_topic}"
    points = summary.get("key_points", [])[:6]

    if not points:
        points = split_sentences(text)[:6]

    palette = [
        {"background": "#a8d8f0", "border": "#5fa8d3"},
        {"background": "#f4e4ad", "border": "#dfc56f"},
        {"background": "#c2bdf5", "border": "#8e86df"},
        {"background": "#f8c8a8", "border": "#e09b6e"},
        {"background": "#c8e9b8", "border": "#90c276"},
        {"background": "#f2c8dc", "border": "#d996b7"},
    ]

    nodes = [
        {
            "id": "topic",
            "label": center_title,
            "group": "topic",
            "x": 0,
            "y": 0,
            "fixed": True,
        }
    ]
    edges = []

    radius = 360
    for idx, point in enumerate(points, start=1):
        angle = (2 * math.pi * (idx - 1)) / max(1, len(points))
        x_pos = int(radius * math.cos(angle))
        y_pos = int(radius * math.sin(angle))
        theme_title = _compact_phrase(point)
        description = _short_description(point)
        color = palette[(idx - 1) % len(palette)]
        label = f"{theme_title}\n\n{description}"

        node_id = f"idea_{idx}"
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "group": "theme",
                "x": x_pos,
                "y": y_pos,
                "fixed": False,
                "color": color,
            }
        )
        edges.append({"from": "topic", "to": node_id, "arrows": "to"})

    # If summary points are too few, supplement with top keywords.
    if len(points) < 4:
        keyword_terms = []
        for kw in keywords:
            if isinstance(kw, dict):
                keyword_terms.append(kw.get("term", ""))
            elif isinstance(kw, str):
                keyword_terms.append(kw)
        keyword_terms = [term for term in keyword_terms if term][: 6 - len(points)]
        for idx, term in enumerate(keyword_terms, start=len(points) + 1):
            angle = (2 * math.pi * (idx - 1)) / 6
            x_pos = int(radius * math.cos(angle))
            y_pos = int(radius * math.sin(angle))
            color = palette[(idx - 1) % len(palette)]
            node_id = f"idea_{idx}"
            nodes.append(
                {
                    "id": node_id,
                    "label": f"{term.title()}\n\nImportant concept from this topic",
                    "group": "theme",
                    "x": x_pos,
                    "y": y_pos,
                    "fixed": False,
                    "color": color,
                }
            )
            edges.append({"from": "topic", "to": node_id, "arrows": "to"})

    return {"nodes": nodes, "edges": edges}


def _detect_heading(line):
    stripped = line.strip()
    if not stripped:
        return None
    if re.match(r"^(module|chapter|unit|topic|lesson)\s+[\w\.\-:]+", stripped, flags=re.IGNORECASE):
        lowered = stripped.lower()
        if lowered.startswith("module"):
            return "module"
        if lowered.startswith("chapter"):
            return "chapter"
        if lowered.startswith("topic"):
            return "topic"
        return "section"
    if len(stripped) <= 80 and stripped.isupper() and len(stripped.split()) <= 8:
        return "topic"
    return None


def segment_content(text):
    normalized = normalize_pdf_text(text)
    lines = [line.strip() for line in normalized.splitlines()]
    sections = []
    current = {"title": "Introduction", "type": "whole", "lines": []}

    for line in lines:
        kind = _detect_heading(line)
        if kind:
            if current["lines"]:
                sections.append(current)
            current = {"title": line, "type": kind, "lines": []}
            continue
        if line:
            current["lines"].append(line)

    if current["lines"]:
        sections.append(current)

    # Fallback for PDFs with weak heading signals.
    if len(sections) <= 1:
        sentences = split_sentences(normalized)
        chunk_size = max(8, len(sentences) // 5) if sentences else 8
        sections = []
        for idx in range(0, len(sentences), chunk_size):
            chunk = sentences[idx: idx + chunk_size]
            if not chunk:
                continue
            sections.append(
                {
                    "title": f"Topic {len(sections) + 1}",
                    "type": "topic",
                    "lines": [" ".join(chunk)],
                }
            )

    enriched = []
    for idx, section in enumerate(sections, start=1):
        section_text = clean_text(" ".join(section["lines"]))
        if len(section_text.split()) < 20:
            continue
        summary = summarize_text(section_text, max_sentences=4)
        keywords = extract_keywords(section_text, top_k=10)
        mindmap = generate_mindmap_data(section_text, keywords)
        enriched.append(
            {
                "id": f"sec_{idx}",
                "title": section["title"],
                "type": section["type"],
                "text": section_text,
                "summary": summary,
                "keywords": keywords,
                "mindmap": mindmap,
            }
        )

    return enriched
