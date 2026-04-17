import math
import random
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


def clean_speech_transcript(text):
    if not text:
        return ""
    # Remove common filler words while keeping sentence punctuation intact.
    filler_pattern = r"\b(um+|uh+|erm+|hmm+|like|you know|i mean|actually|basically|okay|yeah)\b"
    cleaned = re.sub(filler_pattern, " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return clean_text(cleaned)


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
    sentence = re.sub(r"\s+", " ", sentence).strip()
    # Prefer left side of definitions to keep node titles meaningful.
    defn_match = re.match(r"^(.+?)\s+(is|are|refers to|means|defined as)\s+.+$", sentence, flags=re.IGNORECASE)
    if defn_match:
        phrase = defn_match.group(1)
        phrase_words = [token for token in tokenize(phrase) if token not in STOPWORDS]
        if phrase_words:
            return " ".join(phrase_words[:max_words]).title()

    words = [token for token in tokenize(sentence) if token not in STOPWORDS]
    if not words:
        return "Key Idea"
    return " ".join(words[:max_words]).title()


def _short_description(sentence, max_words=18):
    cleaned = re.sub(r"\s+", " ", sentence).strip()
    words = cleaned.split()
    trimmed = " ".join(words[:max_words]).strip()
    return trimmed + ("..." if len(words) > max_words else "")


def _select_mindmap_points(text, fallback_points, max_points=7):
    all_sentences = split_sentences(text)
    if not all_sentences:
        return fallback_points[:max_points]

    words = [token for token in tokenize(text) if token not in STOPWORDS]
    frequencies = Counter(words)
    ranked = []
    seen = set()

    candidate_pool = list(fallback_points) + all_sentences
    for sentence in candidate_pool:
        normalized = re.sub(r"\s+", " ", sentence).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)

        sentence_tokens = [token for token in tokenize(normalized) if token not in STOPWORDS]
        if len(sentence_tokens) < 6:
            continue
        if re.search(r"\b(introduction|conclusion|overview|table|figure|contents)\b", normalized, flags=re.IGNORECASE):
            continue

        score = sum(frequencies.get(token, 0) for token in sentence_tokens)
        if re.search(r"\bis\b|\bare\b|\brefers to\b|\bmeans\b|\bdefined as\b", normalized, flags=re.IGNORECASE):
            score += 8
        if 8 <= len(sentence_tokens) <= 22:
            score += 4
        ranked.append((normalized, score))

    ranked.sort(key=lambda item: item[1], reverse=True)
    selected = [item[0] for item in ranked[:max_points]]
    return selected if selected else fallback_points[:max_points]


def generate_mindmap_data(text, keywords):
    summary = summarize_text(text, max_sentences=7)
    center_topic = summary["title"].replace(" • ", " | ") if summary["title"] else "Core Topic"
    center_title = f"Mind Map\n{center_topic}"
    points = summary.get("key_points", [])[:7]

    if not points:
        points = split_sentences(text)[:7]
    points = _select_mindmap_points(text, points, max_points=7)

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

    radius = 340
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
        keyword_terms = [term for term in keyword_terms if term][: 7 - len(points)]
        for idx, term in enumerate(keyword_terms, start=len(points) + 1):
            angle = (2 * math.pi * (idx - 1)) / 7
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


def _to_title(text):
    return re.sub(r"\s+", " ", text.strip()).title()


def _extract_answer_phrase(sentence):
    normalized = re.sub(r"\s+", " ", sentence).strip(" .")
    if not normalized:
        return ""

    patterns = [
        r"^(.+?)\s+is\s+(?:an?\s+|the\s+)?(.+)$",
        r"^(.+?)\s+are\s+(?:an?\s+|the\s+)?(.+)$",
        r"^(.+?)\s+refers to\s+(.+)$",
        r"^(.+?)\s+means\s+(.+)$",
        r"^(.+?)\s+defined as\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            subject = match.group(1).strip(" ,.-")
            if 1 <= len(subject.split()) <= 8:
                return _to_title(subject)

    tokens = [token for token in tokenize(normalized) if token not in STOPWORDS]
    if not tokens:
        return ""
    return _to_title(" ".join(tokens[:3]))


def _sentence_to_question(sentence, answer_phrase):
    normalized = re.sub(r"\s+", " ", sentence).strip(" .")
    if not normalized:
        return "What is the key concept in this note?"

    if re.search(r"\bis\b|\bare\b|\brefers to\b|\bmeans\b|\bdefined as\b", normalized, flags=re.IGNORECASE):
        return f"What is {answer_phrase.lower()}?"
    return f"Which concept is best described by: \"{normalized}\"?"


def _question_relevance_score(sentence, text_tokens):
    sentence_tokens = [token for token in tokenize(sentence) if token not in STOPWORDS]
    if len(sentence_tokens) < 5:
        return -1
    overlap = sum(1 for token in sentence_tokens if token in text_tokens)
    definition_bonus = 2 if re.search(r"\bis\b|\bare\b|\brefers to\b|\bmeans\b|\bdefined as\b", sentence, flags=re.IGNORECASE) else 0
    return overlap + definition_bonus


def generate_quiz_questions(text, summary=None, keywords=None, max_questions=5):
    summary = summary or {}
    keywords = keywords or []
    text_tokens = set(tokenize(text))
    important_sentences = []
    candidates = list(summary.get("key_points", [])) + split_sentences(text)
    seen = set()
    ranked = []
    for sentence in candidates:
        normalized = re.sub(r"\s+", " ", sentence).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        score = _question_relevance_score(normalized, text_tokens)
        if score < 0:
            continue
        ranked.append((normalized, score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    important_sentences = [item[0] for item in ranked[: max_questions * 2]]

    if not important_sentences:
        return []

    keyword_pool = []
    for kw in keywords:
        if isinstance(kw, dict):
            term = kw.get("term", "")
        else:
            term = str(kw)
        term = term.strip()
        if len(term) >= 3:
            keyword_pool.append(_to_title(term))

    sentence_phrases = []
    for sentence in split_sentences(text):
        phrase = _extract_answer_phrase(sentence)
        if phrase and phrase not in sentence_phrases:
            sentence_phrases.append(phrase)

    distractor_pool = []
    for item in keyword_pool + sentence_phrases:
        if item and item not in distractor_pool:
            distractor_pool.append(item)

    questions = []
    for idx, sentence in enumerate(important_sentences[:max_questions], start=1):
        answer = _extract_answer_phrase(sentence)
        if not answer:
            continue

        lower_answer = answer.lower()
        distractors = [item for item in distractor_pool if item.lower() != lower_answer]
        if len(distractors) < 3:
            distractors.extend(
                [
                    "Core Principle",
                    "Reference Concept",
                    "Primary Framework",
                    "Central Process",
                ]
            )

        options = [answer] + random.sample(distractors, k=3)
        random.shuffle(options)
        cleaned_sentence = re.sub(r"\s+", " ", sentence).strip()
        explanation = (
            f"The note states: \"{cleaned_sentence}\".\n"
            f"Your selected option does not match that statement.\n"
            f"The precise answer is \"{answer}\" based on the original context."
        )
        questions.append(
            {
                "id": f"q_{idx}",
                "question": _sentence_to_question(sentence, answer),
                "options": options,
                "correct_index": options.index(answer),
                "explanation": explanation,
            }
        )

    return questions


def check_quiz_answers(questions, answers):
    total = len(questions)
    score = 0
    details = []

    for question in questions:
        question_id = question.get("id")
        selected_index = answers.get(question_id)
        try:
            selected_index = int(selected_index)
        except (TypeError, ValueError):
            selected_index = -1

        correct_index = question.get("correct_index", -1)
        is_correct = selected_index == correct_index
        if is_correct:
            score += 1

        options = question.get("options", [])
        selected_text = options[selected_index] if 0 <= selected_index < len(options) else "Not answered"
        correct_text = options[correct_index] if 0 <= correct_index < len(options) else ""
        details.append(
            {
                "id": question_id,
                "is_correct": is_correct,
                "selected_index": selected_index,
                "correct_index": correct_index,
                "selected": selected_text,
                "correct": correct_text,
                "explanation": question.get("explanation", ""),
            }
        )

    return {
        "score": score,
        "total": total,
        "percentage": round((score / total) * 100, 2) if total else 0,
        "results": details,
    }
