"""Multi-agent tutoring logic for CodeTutor."""

from __future__ import annotations

from typing import Any

import requests

from src.code_checker import CodeChecker
from src.config import OLLAMA_BASE_URL, OLLAMA_MODEL, TOP_K_RETRIEVAL
from src.guardrails import filter_output_for_attempt
from src.rag import RAGSystem
from src.topics import get_topic_by_id

TUTOR_SYSTEM_PROMPT = """You are a Socratic programming tutor. Guide the student with hints,
not full solutions. Ask leading questions. Reference concepts from the course material.
Do not provide complete code solutions unless the student has made multiple attempts."""

THEORY_SYSTEM_PROMPT = """You are a helpful programming instructor. Answer theory questions
clearly using the provided course context. Be concise and educational. Cite concepts from
the course material when relevant."""


def _hint_style_for_attempt(attempt_count: int) -> str:
    """Escalate tutoring style based on how many hints the student has received."""
    if attempt_count == 0:
        return (
            "Attempt 1 — Ask ONE guiding question only. "
            "Do not include any code, pseudocode, or step-by-step solution."
        )
    if attempt_count == 1:
        return (
            "Attempt 2 — Give a conceptual hint that references the course material. "
            "No complete code solution."
        )
    return (
        "Attempt 3+ — You may provide partial pseudocode or a small illustrative snippet "
        "to help the student unblock, but still encourage them to finish the solution."
    )


class CodeTutorAgents:
    """Coordinates checker, tutor, and theory agents."""

    def __init__(self, rag_system: RAGSystem):
        self.rag = rag_system
        self.checker = CodeChecker()

    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Send a prompt to the local Ollama API and return the response text."""
        url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
        }
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except requests.ConnectionError:
            return (
                "[Ollama unavailable] Think about the problem step by step. "
                "What is the function supposed to return? "
                "Review the course material on functions and try again."
            )
        except requests.RequestException as exc:
            return f"[Error contacting Ollama: {exc}] Please try again later."

    def checker_agent(self, state: dict[str, Any]) -> dict[str, Any]:
        """Check whether the student's code compiles."""
        code = state.get("user_code", "")
        passed, error_message = self.checker.check_syntax(code)
        state["test_passed"] = passed
        if not passed:
            state["hint"] = f"Your code has a syntax error: {error_message}"
        else:
            state["hint"] = "Great job! Your code has no syntax errors."
        return state

    def tutor_agent(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate a Socratic hint using RAG context and Ollama."""
        exercise = state.get("exercise_description", "")
        code = state.get("user_code", "")
        attempt_count = state.get("attempt_count", 0)

        query = f"{exercise} {code}"
        rag_context = self.rag.retrieve(query, top_k=TOP_K_RETRIEVAL)
        state["rag_context"] = rag_context

        hint_style = _hint_style_for_attempt(attempt_count)
        prompt = f"""Exercise:
{exercise}

Student's current code:
{code}

Relevant course material:
{rag_context}

{hint_style}

Provide a Socratic hint to help the student progress."""

        raw_hint = self._call_ollama(prompt, TUTOR_SYSTEM_PROMPT)
        state["hint"] = filter_output_for_attempt(raw_hint, attempt_count)
        state["attempt_count"] = attempt_count + 1
        return state

    def theory_agent(self, question: str, topic_id: str | None = None) -> str:
        """Answer a theory question using RAG context and Ollama, optionally scoped to a topic."""
        topic_header = ""
        if topic_id:
            topic = get_topic_by_id(topic_id)
            if topic:
                topic_header = (
                    f"Topic: {topic['title']}\n"
                    f"Focus area: {topic.get('description', '')}\n\n"
                )

        rag_query = f"{topic_header}{question}"
        rag_context = self.rag.retrieve(rag_query, top_k=TOP_K_RETRIEVAL)
        prompt = f"""{topic_header}Question: {question}

Relevant course material:
{rag_context}

Answer the student's theory question based on the course material for this topic."""

        return self._call_ollama(prompt, THEORY_SYSTEM_PROMPT)
