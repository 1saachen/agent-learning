# Phase 2 Code Organization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Organize runnable code for Phase 2 lessons 2-5 into a testable `phase2` package while preserving the existing lesson 1 entry point.

**Architecture:** Keep data contracts, prompts, provider client, business service, and FastAPI transport in separate modules. Inject a model caller so all tests use deterministic offline fakes; the OpenAI adapter is optional at runtime.

**Tech Stack:** Python 3.13, Pydantic v2, FastAPI, pytest, optional OpenAI SDK.

---

### Task 1: Create package contracts and prompts

**Files:** `app/contracts.py`, `app/prompts.py`, `tests/test_phase2_contracts.py`, `tests/test_phase2_prompts.py`

- [ ] Write tests for valid/invalid `ResumeAnalysis`, request bounds, system prompt rules, and user data placement.
- [ ] Implement Pydantic models and versioned prompt functions.
- [ ] Run the contract and Prompt tests from the repository root.

### Task 2: Add injectable model clients and retry policy

**Files:** `app/client.py`, `tests/test_phase2_client.py`

- [ ] Write tests for success, retryable timeout, non-retryable error, and maximum attempts.
- [ ] Implement `ModelCaller` protocol, deterministic fake, optional OpenAI adapter, and bounded retry helper.
- [ ] Run client tests.

### Task 3: Add analysis service and diagnostics

**Files:** `app/service.py`, `tests/test_phase2_service.py`

- [ ] Write tests for successful analysis, malformed JSON diagnostics, and provider errors.
- [ ] Implement service orchestration and safe diagnostic previews.
- [ ] Run service tests.

### Task 4: Add FastAPI transport

**Files:** `app/api.py`, `tests/test_phase2_api.py`

- [ ] Write TestClient tests for success, validation 422, parse failure 502, and timeout 504.
- [ ] Implement dependency-injected app factory and error mapping.
- [ ] Run API tests.

### Task 5: Document and verify

**Files:** `README.md`, `lesson.md`

- [ ] Document file map and commands.
- [ ] Run full test suite, compile check, and diff check.
- [ ] Commit the organized Phase 2 code.
