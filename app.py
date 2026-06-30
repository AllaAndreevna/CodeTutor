"""CodeTutor Gradio web application."""

from __future__ import annotations

import asyncio

import gradio as gr

from src.agents import CodeTutorAgents
from src.exercises import (
    exercise_choices_for_topic,
    get_exercise_by_id,
    topic_summary_markdown,
)
from src.graph import build_hint_graph, build_practice_graph
from src.guardrails import filter_input
from src.rag import RAGSystem
from src.state import TutorState
from src.topics import get_topic_by_id, load_topics, sample_question_choices, topic_choices

rag_system = RAGSystem()
agents = CodeTutorAgents(rag_system)
practice_graph = build_practice_graph(agents)
hint_graph = build_hint_graph(agents)

DEFAULT_TOPIC = load_topics()[0]["id"] if load_topics() else ""


def _initial_state(code: str, exercise: str, attempt_count: int) -> TutorState:
    return TutorState(
        user_code=code or "",
        exercise_description=exercise or "",
        attempt_count=attempt_count,
        test_passed=False,
        rag_context="",
        hint="",
        input_safe=True,
        blocked_message="",
        needs_tutor=False,
    )


def _run_practice(code: str, exercise: str, attempt_count: int) -> TutorState:
    state = _initial_state(code, exercise, attempt_count)
    return practice_graph.invoke(state)


def _run_hint(code: str, exercise: str, attempt_count: int) -> TutorState:
    state = _initial_state(code, exercise, attempt_count)
    return hint_graph.invoke(state)


def _run_theory(question: str, topic_id: str) -> str:
    is_safe, message = filter_input(question)
    if not is_safe:
        return message
    return agents.theory_agent(question, topic_id=topic_id or None)


def topic_info_markdown(topic_id: str) -> str:
    """Render topic title, description, and linked course document."""
    topic = get_topic_by_id(topic_id)
    if not topic:
        return "_Select a topic to see its description._"
    return (
        f"### {topic['title']}\n\n"
        f"{topic.get('description', '')}\n\n"
        f"**Course material:** `data/course_docs/{topic.get('course_doc', '')}`"
    )


def on_topic_change(topic_id: str) -> tuple:
    """Update exercise list and load the first exercise when topic changes."""
    choices = exercise_choices_for_topic(topic_id) if topic_id else []
    first_id = choices[0][1] if choices else None
    description, starter = load_selected_exercise(first_id, topic_id) if first_id else ("", "")
    return (
        gr.Dropdown(choices=choices, value=first_id),
        topic_info_markdown(topic_id),
        description,
        starter,
    )


def load_selected_exercise(exercise_id: str, topic_id: str) -> tuple[str, str]:
    """Populate description and starter code from a bundled exercise."""
    exercise = get_exercise_by_id(exercise_id, topic_id=topic_id)
    if not exercise:
        return "", ""
    return exercise.get("description", ""), exercise.get("starter_code", "")


async def handle_check(
    code: str,
    exercise: str,
    attempt_count: int,
) -> tuple[str, int, bool, str]:
    """Run LangGraph practice workflow: guard → checker → tutor (on failure)."""
    result = await asyncio.to_thread(_run_practice, code, exercise, attempt_count)
    hint = result.get("hint", "")
    attempt_count = result.get("attempt_count", attempt_count)
    passed = result.get("test_passed", False)
    if not result.get("input_safe", True):
        status = "Input blocked by safety guardrails."
    elif passed:
        status = "Syntax check passed!"
    else:
        status = "Syntax check failed — Socratic hint provided below."
    return hint, attempt_count, passed, status


async def get_hint(
    code: str,
    exercise: str,
    attempt_count: int,
) -> tuple[str, int]:
    """Run LangGraph hint workflow: guard → tutor."""
    result = await asyncio.to_thread(_run_hint, code, exercise, attempt_count)
    return result.get("hint", ""), result.get("attempt_count", attempt_count)


async def ask_theory(question: str, topic_id: str) -> str:
    """Answer a theory question with topic-scoped RAG + Ollama."""
    return await asyncio.to_thread(_run_theory, question, topic_id)


def reset_session(topic_id: str) -> tuple:
    """Reset attempt counter and reload the first exercise for the current topic."""
    choices = exercise_choices_for_topic(topic_id) if topic_id else []
    first_id = choices[0][1] if choices else None
    description, starter = load_selected_exercise(first_id, topic_id) if first_id else ("", "")
    return (
        0,
        starter,
        description,
        "",
        False,
        "",
        gr.Dropdown(choices=choices, value=first_id),
    )


def build_app() -> gr.Blocks:
    """Build and return the Gradio application."""
    topics = topic_choices()
    initial_topic = DEFAULT_TOPIC
    initial_exercises = exercise_choices_for_topic(initial_topic) if initial_topic else []
    initial_exercise_id = initial_exercises[0][1] if initial_exercises else None
    initial_desc, initial_code = (
        load_selected_exercise(initial_exercise_id, initial_topic)
        if initial_exercise_id
        else ("", "")
    )
    initial_samples = sample_question_choices(initial_topic)

    with gr.Blocks(title="CodeTutor - AI Programming Tutor") as demo:
        gr.Markdown("# CodeTutor — AI Programming Tutor")
        gr.Markdown(
            "**Capstone project** · Topic-based curriculum · RAG · LangGraph · "
            "Safety guardrails · Local Ollama LLM"
        )

        attempt_state = gr.State(0)

        with gr.Tab("Code Practice"):
            gr.Markdown(
                "Exercises are grouped by **topic**. Select a topic, then choose an exercise."
            )
            topic_dropdown = gr.Dropdown(
                label="Topic",
                choices=topics,
                value=initial_topic,
            )
            topic_info = gr.Markdown(topic_info_markdown(initial_topic))
            exercise_dropdown = gr.Dropdown(
                label="Exercise",
                choices=initial_exercises,
                value=initial_exercise_id,
            )
            exercise_input = gr.Textbox(
                label="Exercise Description",
                value=initial_desc,
                lines=3,
            )
            code_input = gr.Code(
                label="Your Python Code",
                language="python",
                value=initial_code,
                lines=15,
            )
            with gr.Row():
                check_btn = gr.Button("Check", variant="primary")
                hint_btn = gr.Button("Get Hint")
                reset_btn = gr.Button("Reset")

            status_output = gr.Textbox(label="Status", interactive=False)
            hint_output = gr.Textbox(label="Hint / Feedback", lines=8, interactive=False)
            passed_output = gr.Checkbox(label="Syntax Passed", interactive=False)

            topic_dropdown.change(
                fn=on_topic_change,
                inputs=[topic_dropdown],
                outputs=[exercise_dropdown, topic_info, exercise_input, code_input],
            )

            exercise_dropdown.change(
                fn=load_selected_exercise,
                inputs=[exercise_dropdown, topic_dropdown],
                outputs=[exercise_input, code_input],
            )

            check_btn.click(
                fn=handle_check,
                inputs=[code_input, exercise_input, attempt_state],
                outputs=[hint_output, attempt_state, passed_output, status_output],
            )
            hint_btn.click(
                fn=get_hint,
                inputs=[code_input, exercise_input, attempt_state],
                outputs=[hint_output, attempt_state],
            )
            reset_btn.click(
                fn=reset_session,
                inputs=[topic_dropdown],
                outputs=[
                    attempt_state,
                    code_input,
                    exercise_input,
                    hint_output,
                    passed_output,
                    status_output,
                    exercise_dropdown,
                ],
            )

        with gr.Tab("Theory Q&A"):
            gr.Markdown(
                "Theory questions are grouped by the same topics as coding exercises. "
                "RAG retrieves from the matching course document."
            )
            theory_topic_dropdown = gr.Dropdown(
                label="Topic",
                choices=topics,
                value=initial_topic,
            )
            theory_sample_dropdown = gr.Dropdown(
                label="Sample question (optional)",
                choices=initial_samples,
                value=initial_samples[0] if initial_samples else None,
            )
            question_input = gr.Textbox(
                label="Your Question",
                placeholder="e.g. What is a Python function?",
                lines=3,
            )
            ask_btn = gr.Button("Ask", variant="primary")
            answer_output = gr.Textbox(label="Answer", lines=10, interactive=False)

            def on_theory_topic_change(topic_id: str) -> tuple:
                samples = sample_question_choices(topic_id)
                return (
                    gr.Dropdown(choices=samples, value=samples[0] if samples else None),
                    "",
                )

            theory_topic_dropdown.change(
                fn=on_theory_topic_change,
                inputs=[theory_topic_dropdown],
                outputs=[theory_sample_dropdown, answer_output],
            )
            theory_sample_dropdown.change(
                fn=lambda q: q or "",
                inputs=[theory_sample_dropdown],
                outputs=[question_input],
            )
            ask_btn.click(
                fn=ask_theory,
                inputs=[question_input, theory_topic_dropdown],
                outputs=[answer_output],
            )

        with gr.Tab("Course Topics"):
            gr.Markdown(topic_summary_markdown())
            gr.Markdown(
                """
### How topics are organized

| Layer | Location | Purpose |
|-------|----------|---------|
| **Topic metadata** | `data/topics.json` | Titles, descriptions, sample theory questions |
| **Course material** | `data/course_docs/<topic>.txt` | RAG knowledge base per topic |
| **Exercises** | `data/exercises/<topic>/*.json` | Coding tasks grouped by topic |

This structure keeps theory, retrieval, and practice aligned within each topic.
"""
            )

        with gr.Tab("About"):
            gr.Markdown(
                """
### Integrated Technologies
1. **RAG** — ChromaDB + sentence-transformers over per-topic course documents
2. **LangGraph** — Multi-agent workflow: `guard_input → checker → tutor`
3. **Safety Guardrails** — Jailbreak filtering + attempt-based output masking
4. **Prompt Engineering** — Socratic system prompts with attempt escalation
5. **Local LLM** — Ollama (`codellama:7b-instruct-q4_0`)

### Run Tests
```bash
pytest tests/ -v
```
"""
            )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch()
