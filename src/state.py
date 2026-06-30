"""Shared state schema for LangGraph workflows."""

from typing_extensions import TypedDict


class TutorState(TypedDict, total=False):
    """State passed between LangGraph nodes in the practice workflow."""

    user_code: str
    exercise_description: str
    attempt_count: int
    test_passed: bool
    rag_context: str
    hint: str
    input_safe: bool
    blocked_message: str
    needs_tutor: bool
