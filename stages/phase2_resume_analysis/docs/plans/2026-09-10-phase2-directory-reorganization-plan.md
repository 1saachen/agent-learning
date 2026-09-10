# Phase 2 Directory Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move every Phase 2 resume-analysis artifact into a self-contained stage directory without changing behavior.

**Architecture:** `stages.phase2_resume_analysis` becomes the stable package namespace. Its `app`, `examples`, `exercises`, and `tests` subpackages use absolute imports; data paths are resolved relative to the stage directory.

**Tech Stack:** Python 3.13, Pydantic v2, FastAPI, pytest, OpenAI-compatible DeepSeek SDK.

---

### Task 1: Move Phase 2 artifacts

**Files:** Move current Phase 2 application, examples, exercises, tests, lesson, data, requirements, environment template, specs, and plans into `stages/phase2_resume_analysis/`.

- [ ] Create the stage package directories.
- [ ] Move files without modifying their content.
- [ ] Confirm unrelated untracked paths remain unchanged.

### Task 2: Repair package imports and runtime paths

**Files:** All Python files under `stages/phase2_resume_analysis/`.

- [ ] Replace `phase2` imports with `stages.phase2_resume_analysis.app` imports.
- [ ] Update the Uvicorn module path.
- [ ] Resolve the evaluation data file from the stage directory.
- [ ] Run stage tests and fix only migration-related failures.

### Task 3: Update documentation and test discovery

**Files:** `README.md`, `docs/project-memory.md`, `docs/agent-learning-roadmap.md`, `stages/phase2_resume_analysis/README.md`, `stages/phase2_resume_analysis/lesson.md`, `pytest.ini`.

- [ ] Replace old paths and commands with the new stage paths.
- [ ] Add a concise stage-local README.
- [ ] Restrict pytest discovery to project stage tests.

### Task 4: Verify and publish

- [ ] Run root pytest, compileall, Mock example, and evaluation data load.
- [ ] Search for stale old import paths and commands.
- [ ] Commit only intended tracked files and push to `origin/main`.
