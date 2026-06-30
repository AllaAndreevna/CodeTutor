"""Load structured coding exercises grouped by topic."""

import json
from pathlib import Path

from src.config import EXERCISES_DIR
from src.topics import load_topics


def load_exercises(
    exercises_dir: Path | None = None,
    topic_id: str | None = None,
) -> list[dict]:
    """
    Load exercise JSON files from topic subfolders.

    Layout: data/exercises/<topic_id>/*.json
    """
    directory = Path(exercises_dir or EXERCISES_DIR)
    if not directory.exists():
        return []

    exercises: list[dict] = []
    topic_dirs = sorted(directory.iterdir()) if directory.is_dir() else []

    for topic_dir in topic_dirs:
        if not topic_dir.is_dir():
            continue
        folder_topic = topic_dir.name
        if topic_id and folder_topic != topic_id:
            continue

        for path in sorted(topic_dir.glob("*.json")):
            with path.open(encoding="utf-8") as handle:
                exercise = json.load(handle)
                exercise.setdefault("id", path.stem)
                exercise.setdefault("topic", folder_topic)
                exercises.append(exercise)

    return exercises


def exercises_by_topic(exercises_dir: Path | None = None) -> dict[str, list[dict]]:
    """Group exercises by topic id."""
    grouped: dict[str, list[dict]] = {}
    for exercise in load_exercises(exercises_dir):
        topic = exercise.get("topic", "general")
        grouped.setdefault(topic, []).append(exercise)
    return grouped


def exercise_choices_for_topic(
    topic_id: str,
    exercises_dir: Path | None = None,
) -> list[tuple[str, str]]:
    """Return (label, exercise_id) pairs for one topic."""
    exercises = load_exercises(exercises_dir, topic_id=topic_id)
    return [(ex.get("title", ex["id"]), ex["id"]) for ex in exercises]


def get_exercise_by_id(
    exercise_id: str,
    topic_id: str | None = None,
    exercises_dir: Path | None = None,
) -> dict | None:
    """Look up a single exercise by id (optionally scoped to a topic)."""
    if not exercise_id:
        return None
    for exercise in load_exercises(exercises_dir, topic_id=topic_id):
        if exercise.get("id") == exercise_id:
            return exercise
    return None


def topic_summary_markdown(exercises_dir: Path | None = None) -> str:
    """Build a markdown overview of topics and their exercises."""
    lines = ["### Course Topics\n"]
    grouped = exercises_by_topic(exercises_dir)
    for topic in load_topics():
        tid = topic["id"]
        title = topic["title"]
        desc = topic.get("description", "")
        doc = topic.get("course_doc", "")
        ex_list = grouped.get(tid, [])
        lines.append(f"#### {title}")
        lines.append(f"{desc}")
        lines.append(f"- **Course material:** `{doc}`")
        lines.append(f"- **Exercises:** {len(ex_list)}")
        for ex in ex_list:
            lines.append(f"  - {ex.get('title', ex['id'])}")
        lines.append("")
    return "\n".join(lines)
