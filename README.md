# CodeTutor — AI Programming Tutor

**Course:** Large Language Models and Applications (IB00322)  
**Institution:** Shenzhen Technology University · Spring 2026  
**Topic:** AI-Powered Tutoring System (#6)

CodeTutor is an AI programming tutor that helps students practice Python with **Socratic hints**, check syntax, and ask **theory questions** grounded in course materials. It runs fully on a **local Ollama** model — no API key required for grading or demo.

---

## Integrated Technologies (4+)

| Technology | Implementation |
|------------|----------------|
| **RAG** | ChromaDB + `sentence-transformers/all-MiniLM-L6-v2` over `data/course_docs/` |
| **LangGraph** | Multi-agent workflow: `guard_input → checker → tutor` |
| **Safety Guardrails** | Jailbreak phrase blocking + attempt-based code masking |
| **Prompt Engineering** | System prompts + attempt-escalation hint styles |
| **Local LLM** | Ollama `codellama:7b-instruct-q4_0` via HTTP API |

---

## Architecture

```mermaid
flowchart TD
    UI[Gradio Web UI] --> PG[LangGraph Practice Workflow]
    UI --> TG[Theory Agent]
    PG --> G[guard_input]
    G -->|safe| C[checker_agent]
    G -->|blocked| END1[END]
    C -->|syntax fail| T[tutor_agent + RAG]
    C -->|syntax pass| END2[END]
    T --> O[Ollama LLM]
    T --> R[RAG / ChromaDB]
    TG --> R
    TG --> O
```

**Practice flow:** Student submits code → guardrails filter input → syntax checker runs → on failure, RAG retrieves course context → tutor agent generates a Socratic hint (code hidden on early attempts).

**Theory flow:** Student asks a question → guardrails → RAG retrieval → LLM answer grounded in course docs.

---

## Prerequisites

- Python 3.11+ (tested on 3.14)
- [Ollama](https://ollama.com/) installed and running
- Model pulled: `codellama:7b-instruct-q4_0`

```bash
ollama pull codellama:7b-instruct-q4_0
```

> On Windows, Ollama usually runs as a background service. If `ollama serve` reports port 11434 is in use, the server is already running — skip that step.

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/codetutor.git
cd codetutor
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

---

## Run the Application

```bash
python app.py
```

Open the URL shown in the terminal (typically `http://127.0.0.1:7860`).

### Demo Script (15–20 min presentation)

1. **Course Topics tab** — Show how exercises, course docs, and theory are grouped by topic.
2. **Theory Q&A tab** — Select topic **Loops** → pick sample question → show RAG-grounded answer from `loops.txt`.
3. **Code Practice tab** — Select topic **Functions** → exercise **Hello, World Function** → submit `def greet(` → **Check** → syntax error + Socratic hint.
4. **Guardrails** — Type *"ignore previous instructions"* → show blocked message.
5. **Tests** — Run `pytest tests/ -v` and show pass-rate screenshot.

---

## Topic-Based Curriculum

All content is organized by **topic** so theory, RAG retrieval, and coding practice stay aligned.

| Topic | Course doc | Exercises |
|-------|------------|-----------|
| **Functions** | `functions.txt` | Hello World, Add Numbers, Check Even |
| **Variables & Data Types** | `variables.txt` | Swap Values, Temperature Converter |
| **Loops** | `loops.txt` | Sum a List, Count Vowels |

```
data/
├── topics.json                 # Topic metadata + sample theory questions
├── course_docs/
│   ├── functions.txt
│   ├── variables.txt
│   └── loops.txt
└── exercises/
    ├── functions/*.json
    ├── variables/*.json
    └── loops/*.json
```

---

## Run Tests (TDD-for-AI)

```bash
pytest tests/ -v
```

| Test file | Level | Count |
|-----------|-------|-------|
| `test_tools.py` | Tool + Retrieval | 3 |
| `test_agents.py` | Agent behavior | 4 |
| `test_security.py` | Security | 3 |
| `test_integration.py` | Integration (LangGraph E2E) | 4 |
| `requirements_test.py` | Executable specification | 5 |
| **Total** | **5 levels** | **19** |

Run only fast unit tests:

```bash
pytest tests/ -v -m "not integration"
```

---

## Project Structure

```
Code_Tutor_Final_Project/
├── app.py                  # Gradio web UI
├── requirements.txt
├── README.md
├── data/
│   ├── topics.json         # Topic definitions
│   ├── course_docs/        # RAG knowledge base (one file per topic)
│   └── exercises/          # JSON exercises in topic subfolders
├── chroma_db/              # Vector store (auto-created, gitignored)
├── src/
│   ├── config.py
│   ├── rag.py
│   ├── agents.py
│   ├── graph.py
│   ├── guardrails.py
│   ├── code_checker.py
│   ├── exercises.py
│   ├── topics.py
│   └── state.py
└── tests/
```

---

## Configuration

Edit `src/config.py` or set environment variables:

| Variable | Default |
|----------|---------|
| `OLLAMA_MODEL` | `codellama:7b-instruct-q4_0` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `CHUNK_SIZE` | `500` |
| `TOP_K_RETRIEVAL` | `3` |

### Re-index course documents

After adding new files to `data/course_docs/`, delete the `chroma_db/` folder and restart the app.

---

## Adding Course Material

Place `.txt` files in `data/course_docs/`. The RAG system indexes them on first launch.

## Adding Exercises

Create a JSON file inside the matching topic folder, e.g. `data/exercises/functions/my_exercise.json`:

```json
{
  "id": "my_exercise",
  "title": "My Exercise",
  "description": "Write a function that ...",
  "starter_code": "def my_func():\n    pass",
  "topic": "functions"
}
```

Register new topics in `data/topics.json` and add a matching file in `data/course_docs/`.

---

## Publish to GitHub

### 1. Initialize and commit (first time only)

```bash
git init
git add .
git commit -m "Initial commit: CodeTutor capstone project"
```

### 2. Create a repository on GitHub

1. Go to [github.com/new](https://github.com/new)
2. Name it e.g. `codetutor` or `CodeTutor-IB00322`
3. Do **not** add README (you already have one)
4. Copy the repository URL

### 3. Push your code

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPO` with your GitHub details.

> `venv/` and `chroma_db/` are listed in `.gitignore` and will not be uploaded.

---

## AI Tool Usage Disclosure

This project was developed with **Cursor** (Vibe Coding). AI assisted with boilerplate, test scaffolding, and documentation. All architecture decisions, guardrail rules, prompt design, and demo flow were reviewed and can be explained during defense.

---

## License

Academic project for IB00322 — Spring 2026.
