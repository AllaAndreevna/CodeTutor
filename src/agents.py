"""Multi-agent tutoring logic for CodeTutor."""

from __future__ import annotations

from typing import Any

from src.code_checker import CodeChecker
from src.config import OLLAMA_MODEL, TOP_K_RETRIEVAL
from src.guardrails import filter_output_for_attempt
from src.ollama_client import check_ollama_status, generate as ollama_generate
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


def _theory_rag_fallback(question: str, rag_context: str, topic_title: str | None = None) -> str:
    """Return a useful theory answer from RAG when Ollama is offline."""
    status = check_ollama_status()
    header = f"**{topic_title}** — " if topic_title else ""
    if rag_context.strip():
        return (
            f"{header}Answer based on course materials:\n\n"
            f"{rag_context.strip()}\n\n"
            f"---\n"
            f"*Note: Ollama is offline ({status.message}). "
            f"This answer was retrieved directly from the course documents via RAG.*"
        )
    return (
        f"Could not reach Ollama and no matching course material was found.\n\n"
        f"{status.message}\n\n"
        f"Please start Ollama, then run: `ollama pull {OLLAMA_MODEL}`"
    )


def _tutor_offline_fallback(rag_context: str) -> str:
    """Fallback hint when Ollama is offline during code practice."""
    status = check_ollama_status()
    if rag_context.strip():
        return (
            "Ollama is offline. Here is relevant material from the course:\n\n"
            f"{rag_context.strip()}\n\n"
            "Try to solve the exercise using these concepts. "
            f"To get AI hints, start Ollama: {status.message}"
        )
    return (
        "[Ollama unavailable] Think about the problem step by step. "
        "What is the function supposed to return? "
        f"Start Ollama to enable AI hints. ({status.message})"
    )


class CodeTutorAgents:
    """Coordinates checker, tutor, and theory agents."""

    def __init__(self, rag_system: RAGSystem):
        self.rag = rag_system
        self.checker = CodeChecker()
        self.ollama_status = check_ollama_status()

    def _call_ollama(
        self,
        prompt: str,
        system_prompt: str,
        *,
        offline_fallback: str | None = None,
    ) -> str:
        """Send a prompt to the local Ollama API and return the response text."""
        try:
            return ollama_generate(prompt, system_prompt)
        except (ConnectionError, OSError):
            if offline_fallback is not None:
                return offline_fallback
            status = check_ollama_status()
            return (
                f"[Ollama unavailable] {status.message}"
            )

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

        raw_hint = self._call_ollama(
            prompt,
            TUTOR_SYSTEM_PROMPT,
            offline_fallback=_tutor_offline_fallback(rag_context),
        )
        state["hint"] = filter_output_for_attempt(raw_hint, attempt_count)
        state["attempt_count"] = attempt_count + 1
        return state

    def theory_agent(self, question: str, topic_id: str | None = None) -> str:
        """Answer a theory question using RAG context and Ollama, optionally scoped to a topic."""
        topic_header = ""
        topic_title: str | None = None
        course_doc: str | None = None

        if topic_id:
            topic = get_topic_by_id(topic_id)
            if topic:
                topic_title = topic["title"]
                course_doc = topic.get("course_doc")
                topic_header = (
                    f"Topic: {topic['title']}\n"
                    f"Focus area: {topic.get('description', '')}\n\n"
                )

        rag_query = f"{topic_header}{question}"
        rag_context = self.rag.retrieve(
            rag_query, top_k=TOP_K_RETRIEVAL, source=course_doc
        )

        rag_answer = _theory_rag_fallback(question, rag_context, topic_title)

        # Refresh Ollama status on each theory request
        status = check_ollama_status()
        self.ollama_status = status

        if not status.available:
            return rag_answer

        prompt = f"""{topic_header}Question: {question}

Relevant course material:
{rag_context}

Answer the student's theory question clearly based on the course material."""

        try:
            llm_answer = ollama_generate(prompt, THEORY_SYSTEM_PROMPT)
            if llm_answer and llm_answer.strip():
                return llm_answer.strip()
        except Exception:
            pass

        return rag_answer
