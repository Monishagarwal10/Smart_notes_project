import json
import os
import uuid
from datetime import datetime


def _storage_path(base_dir):
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "saved_notes.json")


def load_sessions(base_dir):
    path = _storage_path(base_dir)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError:
            return []


def save_session(base_dir, payload):
    sessions = load_sessions(base_dir)
    session = {
        "id": str(uuid.uuid4()),
        "title": payload.get("title", "Untitled Session"),
        "source_type": payload.get("source_type", "manual"),
        "raw_text": payload.get("raw_text", ""),
        "summary": payload.get("summary", {}),
        "keywords": payload.get("keywords", []),
        "mindmap": payload.get("mindmap", {"nodes": [], "edges": []}),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    sessions.append(session)

    path = _storage_path(base_dir)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(sessions, file, indent=2, ensure_ascii=False)
    return session
