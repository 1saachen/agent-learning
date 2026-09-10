# Resume Analysis Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Phase 2 modules into a complete, runnable, testable resume analysis project.

**Architecture:** Reuse the existing injected DeepSeek-compatible client and FastAPI service. Add a small evaluation module, sample dataset, CLI examples, and project documentation without introducing a database or frontend.

**Tech Stack:** Python 3.13, Pydantic v2, FastAPI, pytest, optional OpenAI SDK, JSONL.

---

### Task 1: Add evaluation metrics

**Files:** `app/evaluation.py`, `data/eval_cases.jsonl`, `tests/test_phase2_evaluation.py`

- [ ] Test JSONL loading, exact skill-hit calculation, and aggregate metrics.
- [ ] Implement deterministic evaluation helpers that accept an injected analyzer.
- [ ] Run evaluation tests.

### Task 2: Add runnable examples

**Files:** `examples/mock_resume_analysis.py`, `examples/deepseek_resume_analysis.py`

- [ ] Add a no-network Mock example that prints a structured result.
- [ ] Add an explicitly configured DeepSeek example that reads environment variables only.
- [ ] Compile both examples.

### Task 3: Complete project documentation

**Files:** `README.md`, `lesson.md`, repository `docs/project-memory.md`

- [ ] Document project flow, file map, API request, example commands, evaluation command, and expected error codes.
- [ ] Keep API keys out of all tracked files.

### Task 4: Verify and publish

- [ ] Run the full pytest suite and compileall.
- [ ] Run the offline example and evaluator.
- [ ] Inspect diff, commit, and push to `origin/main`.
