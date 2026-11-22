# CodeTutor — Project Report 

**Course:** IB00322 — Large Language Models and Applications  
**Institution:** Shenzhen Technology University  
**Semester:** Spring 2026  
**Project:** CodeTutor — AI Programming Tutor (Topic #6)  
**Author:** Alla Chernova

---

## 1. Project Overview

### 1.1 Background

Large language models are increasingly used in education, but generic chatbots pose pedagogical risks: students often receive complete solutions instead of guided learning, answers may be factually incorrect or detached from a structured curriculum, and there are few built-in safety controls against prompt injection. For introductory Python courses, instructors need tools that combine automated feedback with Socratic tutoring principles.

### 1.2 Problem Statement

Beginner programmers need an AI assistant that:
- Checks code for syntax errors
- Provides hints rather than full solutions on early attempts
- Answers theory questions grounded in course materials
- Blocks jailbreak and prompt-injection attacks
- Runs locally without paid API keys (instructor-verifiable)

### 1.3 Project Goals

CodeTutor is a web-based AI programming tutor that integrates RAG, multi-agent orchestration (LangGraph), safety guardrails, and prompt engineering. Content is organized by **topic** (Functions, Variables, Loops) so theory, retrieval, and exercises remain aligned.

### 1.4 Scope

**In scope:** Python syntax checking, Socratic hints, topic-based theory Q&A, local Ollama LLM, Gradio UI, pytest test suite.  
**Out of scope (future work):** Code execution sandbox, semantic test validation, user accounts, MCP tools.

---

## 2. System Design

### 2.1 Architecture

The system follows a layered architecture:

1. **Presentation layer** — Gradio web UI (`app.py`) with four tabs: Code Practice, Theory Q&A, Course Topics, About.
2. **Orchestration layer** — LangGraph `StateGraph` workflows (`src/graph.py`).
3. **Agent layer** — Checker, Tutor, and Theory agents (`src/agents.py`).
4. **Knowledge layer** — RAG over ChromaDB (`src/rag.py`).
5. **LLM layer** — Ollama HTTP API (`src/ollama_client.py`).


### 2.2 LangGraph Workflow

**Practice workflow:**
```
START → guard_input → checker → (fail) → tutor → END
                      └→ (pass) ─────────────→ END
```

**Theory workflow:** guardrails → RAG retrieval (topic-scoped) → Ollama (or RAG fallback).

### 2.3 Topic-Based Curriculum

| Topic | Course doc | Exercises |
|-------|------------|-----------|
| Functions | functions.txt | 3 exercises |
| Variables | variables.txt | 2 exercises |
| Loops | loops.txt | 2 exercises |

Metadata in `data/topics.json`; exercises in `data/exercises/<topic>/`.

### 2.4 Technology Stack

| Technology | Role |
|------------|------|
| RAG | ChromaDB + all-MiniLM-L6-v2 embeddings |
| LangGraph | Multi-agent routing and conditional edges |
| Guardrails | Input jailbreak filter + output code masking |
| Prompt Engineering | Socratic tutor + attempt escalation |
| Ollama | Local LLM (codellama:7b-instruct-q4_0) |
| Gradio | Web UI |
| pytest | TDD-for-AI test suite (19 tests) |

---

## 3. Core Implementation

### 3.1 RAG Pipeline

Course documents in `data/course_docs/` are loaded, split into 500-character chunks with 50-character overlap, embedded, and stored in ChromaDB. Retrieval uses cosine similarity with top-k=3. Topic-scoped retrieval filters by `source` metadata (e.g., `loops.txt`).


### 3.2 Agents

- **Checker Agent** — `compile()` and `ast.parse()` for syntax validation.
- **Tutor Agent** — RAG context + Ollama + output guardrails; increments `attempt_count`.
- **Theory Agent** — Topic-scoped RAG + Ollama; RAG-only fallback when Ollama offline.

### 3.3 Guardrails

**Input:** Blocklist of jailbreak phrases (`src/guardrails.py`).  
**Output:** On attempts 0–1, fenced code blocks removed from tutor hints; attempt 2+ allows partial code.

### 3.4 Prompt Engineering

Tutor system prompt enforces Socratic method. Attempt-escalation instructions change hint style: guiding questions → conceptual hints → partial pseudocode.


### 3.5 AI Tool Usage (Cursor / Vibe Coding)

Developed with Cursor AI-assisted programming. AI helped with boilerplate, test scaffolding, and documentation. Architecture decisions, guardrail rules, topic structure, and all test cases were reviewed and can be explained during defense.

---

## 4. Testing and Quality Checks (TDD-for-AI)

### 4.1 Test Strategy

| Level | File | Count | Focus |
|-------|------|-------|-------|
| Tool | test_tools.py | 3 | Syntax checker, RAG retrieval |
| Behavior | test_agents.py | 4 | Agent logic with mocks |
| Security | test_security.py | 3 | Jailbreak, output filtering |
| Integration | test_integration.py | 4 | LangGraph E2E, topic loading |
| Executable spec | requirements_test.py | 5 | REQ-001 to REQ-005 |

**Total: 19 tests, 100% pass rate.**

### 4.2 Executable Requirements

Example (REQ-004):
```python
is_safe, msg = filter_input("ignore previous instructions ...")
assert is_safe is False
```

### 4.3 Lab 09 Quality Checks

12 manual checks (functional, security, boundary, performance) — all passed. See `docs/LAB09_REPORT.md` Section 3.

---

## 5. Improvements from Cross-Team Feedback

### 5.1 Feedback on CodeTutor (from professor and peers)

| Feedback | Action |
|----------|--------|
| Group exercises by topic (professor, mid-presentation) | Topic dropdown, folder structure, Course Topics tab |
| Theory fails when Ollama offline | RAG fallback + status indicator (v1.2.0) |
| Setup difficult on Windows | `run.bat`, offline embedding load, README troubleshooting |

### 5.2 Lessons from testing another team's project (MEDEC)

While cross-team testing the **Medical Compliance AI Assistant / MEDEC Medical Compliance KB**, I confirmed both core functions worked (RAG compliance query and multi-agent document review). However, their missing root `requirements.txt` and incomplete Quick Start made setup slow — the same issues called out in our Lab 09 review. This validated CodeTutor's emphasis on:

- A complete `requirements.txt` at project root
- `README.md` with install, run, and test commands
- `run.bat` for one-click Windows startup
- Automated tests runnable via `pytest tests/ -v`

Their multi-agent supervisor pipeline for document review was a strong design reference for how LangGraph-style orchestration can structure complex workflows — similar to our `guard_input → checker → tutor` graph in CodeTutor.

---

## 6. Summary and Personal Reflections

### 6.1 Achievements

- Complete runnable AI tutoring system with 5 integrated technologies
- 19 automated tests across 5 levels
- Topic-aligned curriculum addressing pedagogical requirements
- Local Ollama support for instructor verification

### 6.2 Challenges

The biggest challenge was integrating multiple components (RAG, LangGraph, Ollama, Gradio) into a coherent user experience while maintaining testability. Windows-specific issues (localhost IPv6, HuggingFace SSL, Ollama connectivity) required additional engineering beyond the core architecture.

### 6.3 Future Work

- MCP protocol for external tools (code runner, linter)
- Semantic exercise validation with test cases
- Instructor analytics dashboard
- LoRA fine-tuning on tutoring dialogues

### 6.4 Individual Contribution

Alla Chernova — sole developer: requirements, architecture, implementation, testing, documentation, presentation, Lab 09 quality checks.

---

## References

- Course capstone rubric IB00322 Spring 2026
- LangGraph documentation: https://langchain-ai.github.io/langgraph/
- ChromaDB documentation: https://docs.trychroma.com/
- Ollama documentation: https://ollama.com/

---

