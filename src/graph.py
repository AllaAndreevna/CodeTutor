"""LangGraph multi-agent workflow for CodeTutor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from langgraph.graph import END, START, StateGraph

from src.guardrails import filter_input
from src.state import TutorState

if TYPE_CHECKING:
    from src.agents import CodeTutorAgents


def _route_after_guard(state: TutorState) -> Literal["checker", "__end__"]:
    if state.get("input_safe", True):
        return "checker"
    return "__end__"


def _route_after_checker(state: TutorState) -> Literal["tutor", "__end__"]:
    if state.get("needs_tutor", False):
        return "tutor"
    return "__end__"


def build_practice_graph(agents: CodeTutorAgents):
    """
    Build the practice workflow graph:

        START → guard_input → checker → (fail) → tutor → END
                              └→ (pass) ─────────────→ END
    """

    def guard_input_node(state: TutorState) -> dict:
        text = f"{state.get('user_code', '')} {state.get('exercise_description', '')}"
        is_safe, message = filter_input(text)
        if is_safe:
            return {"input_safe": True, "blocked_message": ""}
        return {
            "input_safe": False,
            "blocked_message": message,
            "hint": message,
        }

    def checker_node(state: TutorState) -> dict:
        return agents.checker_agent(dict(state))

    def tutor_node(state: TutorState) -> dict:
        updated = agents.tutor_agent(dict(state))
        existing_hint = state.get("hint", "")
        tutor_hint = updated.get("hint", "")
        if existing_hint and tutor_hint:
            updated["hint"] = f"{existing_hint}\n\n{tutor_hint}"
        return updated

    def mark_needs_tutor(state: TutorState) -> dict:
        return {"needs_tutor": not state.get("test_passed", False)}

    graph = StateGraph(TutorState)
    graph.add_node("guard_input", guard_input_node)
    graph.add_node("checker", checker_node)
    graph.add_node("mark_tutor", mark_needs_tutor)
    graph.add_node("tutor", tutor_node)

    graph.add_edge(START, "guard_input")
    graph.add_conditional_edges(
        "guard_input",
        _route_after_guard,
        {"checker": "checker", "__end__": END},
    )
    graph.add_edge("checker", "mark_tutor")
    graph.add_conditional_edges(
        "mark_tutor",
        _route_after_checker,
        {"tutor": "tutor", "__end__": END},
    )
    graph.add_edge("tutor", END)

    return graph.compile()


def build_hint_graph(agents: CodeTutorAgents):
    """Build hint-only workflow: guard_input → tutor."""

    def guard_input_node(state: TutorState) -> dict:
        text = f"{state.get('user_code', '')} {state.get('exercise_description', '')}"
        is_safe, message = filter_input(text)
        if is_safe:
            return {"input_safe": True, "blocked_message": ""}
        return {"input_safe": False, "blocked_message": message, "hint": message}

    def tutor_node(state: TutorState) -> dict:
        return agents.tutor_agent(dict(state))

    graph = StateGraph(TutorState)
    graph.add_node("guard_input", guard_input_node)
    graph.add_node("tutor", tutor_node)

    graph.add_edge(START, "guard_input")
    graph.add_conditional_edges(
        "guard_input",
        _route_after_guard,
        {"checker": "tutor", "__end__": END},
    )
    graph.add_edge("tutor", END)

    return graph.compile()
