# Cross-Team Review Form

**Reviewer:** Alla Chernova
**Course:** IB00322 — Large Language Models and Applications  
**Date:** 2nd of July 2026

---

## System Under Review


| Item                                  | Your notes                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Team tested**                       | Classmate's team 张佳琪                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **Project name**                      | Medical Compliance AI Assistant / MEDEC Medical Compliance KB                                                                                                                                                                                                                                                                                                                                                                                                 |
| **Setup: could you run it? (yes/no)** | **Yes**                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Setup notes**                       | Verified backend with `python -m py_compile scripts/medec_kb/analyze_medical_compliance.py scripts/medec_kb/fastapi_app.py scripts/medec_kb/agent/supervisor_agent.py`. Ran `python -m unittest tests.test_chat_router tests.test_medical_compliance_ui -v` successfully. App starts via `uvicorn scripts.medec_kb.fastapi_app:app --reload` when FastAPI/Uvicorn are installed. No root `requirements.txt` — dependencies must be inferred from code/README. |


---



## Core Functions


| Function                                                                                     | Works?     | Issue (if any)                                                                                                                       |
| -------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Core function 1:** Medical compliance RAG query (`/analyze`, `/chat`)                      | ☑ Yes ☐ No | Routes questions to local analyzer; retrieves evidence from MEDEC knowledge base. No functional issue found.                         |
| **Core function 2:** Document upload + multi-agent compliance report (`/analyze-agent-file`) | ☑ Yes ☐ No | UI supports file upload; pipeline parses documents, retrieves evidence, assesses risks, returns traceable report. Works as expected. |
| **Core function 3 (optional):** UI chat router tests                                         | ☑ Yes ☐ No | `tests.test_chat_router` and `tests.test_medical_compliance_ui` pass.                                                                |


---



## Bugs Found


| Bug   | Severity   | Description                                                                           | Steps to reproduce                                                                                                                           |
| ----- | ---------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Bug 1 | **Medium** | No root `requirements.txt` — new testers cannot install dependencies with one command | Clone repo on a fresh machine; try `pip install -r requirements.txt` → file missing; must read code to find FastAPI, Uvicorn, ChromaDB, etc. |
| Bug 2 | **Low**    | Broken Chinese encoding in README clinical-claim review example                       | Open README on Windows; sample medical text in command example displays as garbled characters                                                |


---



## Improvement Suggestion

**One concrete improvement for the other team:**

> Add a short **"Quick Start for Testers"** section with: (1) exact `pip install` commands for all dependencies, (2) how to start the server (`uvicorn ...`), (3) one sample `/chat` JSON request with expected response fields, (4) one sample file-upload request to `/analyze-agent-file`, and (5) a screenshot or example output. This would make cross-team and instructor testing much faster and more reproducible.

---



## Feedback Received on CodeTutor (our project)


| Reviewer                     | Feedback                             | Our action                                                                |
| ---------------------------- | ------------------------------------ | ------------------------------------------------------------------------- |
| Professor (mid-presentation) | Exercises should be grouped by topic | ✅ Topic-based curriculum (`data/topics.json`, topic folders, UI dropdown) |
| Peer testing                 | Theory fails when Ollama offline     | ✅ RAG fallback + Ollama status indicator (v1.2.0)                         |
| Self-review after MEDEC test | Need clearer Quick Start for testers | ✅ `run.bat`, README troubleshooting, offline model loading                |


---

*Submited with Lab 09 package*