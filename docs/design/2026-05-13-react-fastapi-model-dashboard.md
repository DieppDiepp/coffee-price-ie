# React + FastAPI Model Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit dashboard with a React + FastAPI model dashboard.

**Architecture:** FastAPI exposes model/dashboard JSON by reusing the existing Python modules under `dashboard/`. React + Vite renders a professional analytics cockpit and calls the API.

**Tech Stack:** Python, FastAPI, scikit-learn, google-genai, React, TypeScript, Vite, Recharts, Lucide icons, Vitest.

---

### Task 1: Backend API Contract

**Files:**
- Create: `api/__init__.py`
- Create: `api/schemas.py`
- Create: `api/services.py`
- Create: `api/main.py`
- Test: `tests/test_api.py`

- [ ] Write failing FastAPI tests for metadata and prediction endpoints.
- [ ] Run the targeted API tests and confirm they fail because `api.main` does not exist.
- [ ] Implement schemas, services, and FastAPI routes.
- [ ] Run the targeted API tests and confirm they pass.

### Task 2: Frontend React App

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/format.ts`
- Create: `frontend/src/styles.css`
- Test: `frontend/src/format.test.ts`

- [ ] Write failing frontend utility tests for price formatting, percentage formatting, and direction labels.
- [ ] Run Vitest and confirm tests fail because utilities do not exist.
- [ ] Implement React app, API client, formatting utilities, and cockpit styling.
- [ ] Run frontend tests and build.

### Task 3: Remove Streamlit Runtime

**Files:**
- Delete: `dashboard/app.py`
- Modify: `requirements.txt`
- Modify: `tests/test_dashboard_ui_copy.py`
- Create: `README-dashboard.md`

- [ ] Remove Streamlit UI file and Streamlit dependency.
- [ ] Replace Streamlit copy test with a test that confirms backend/frontend files exist and Streamlit is not required.
- [ ] Document how to run FastAPI and React.
- [ ] Run all Python tests.

### Task 4: End-to-End Verification

**Files:**
- No new files expected.

- [ ] Start FastAPI backend.
- [ ] Start React Vite dev server.
- [ ] Open the app with Playwright.
- [ ] Verify the page renders Vietnamese copy, the chart area is visible, and no console errors are emitted.
