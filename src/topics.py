"""Topic definitions and helpers for grouped course content."""

import json
from pathlib import Path

from src.config import DATA_DIR

TOPICS_FILE = DATA_DIR / "topics.json"


def load_topics(topics_file: Path | None = None) -> list[dict]:
    """Load topic metadata sorted by order."""
    path = Path(topics_file or TOPICS_FILE)
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    topics = data.get("topics", [])
    return sorted(topics, key=lambda t: t.get("order", 0))


def get_topic_by_id(topic_id: str, topics_file: Path | None = None) -> dict | None:
    """Look up a topic by id."""
    if not topic_id:
        return None
    for topic in load_topics(topics_file):
        if topic.get("id") == topic_id:
            return topic
    return None


def topic_choices(topics_file: Path | None = None) -> list[tuple[str, str]]:
    """Return (label, topic_id) pairs for Gradio dropdown."""
    return [(t["title"], t["id"]) for t in load_topics(topics_file)]


def sample_question_choices(topic_id: str, topics_file: Path | None = None) -> list[str]:
    """Return sample theory questions for a topic."""
    topic = get_topic_by_id(topic_id, topics_file)
    if not topic:
        return []
    return topic.get("sample_questions", [])
