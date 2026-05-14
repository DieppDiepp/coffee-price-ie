# React + FastAPI Model Dashboard Design

## Goal
Replace the Streamlit model dashboard with a React + FastAPI demo focused only on coffee price model prediction, Gemini comparison, and ground truth comparison.

## Scope
- Build a professional analytics cockpit UI in React.
- Keep the existing Python model/data modules as backend services.
- Support coffee type, feature version, prediction date, ML prediction, Gemini prediction, ground truth, chart data, feature snapshot, and version comparison.
- Remove Streamlit UI and dependency from the runnable dashboard.
- Do not build the data dashboard.

## Architecture
- `api/` exposes FastAPI endpoints for metadata, prediction, Gemini prediction, and version comparison.
- `dashboard/` remains a Python model/data library for loading CSV data, training fallback models, loading registry checkpoints, and calling Gemini.
- `frontend/` contains the React + Vite + TypeScript app.
- React calls FastAPI through a small API client. Backend returns presentation-ready JSON so the UI does not duplicate model logic.

## UI Direction
The UI uses the selected Analytics Cockpit direction:
- Fixed left sidebar for coffee type, feature version, date, and Gemini action.
- Main content with compact metric cards, prediction comparison table, animated price chart, version comparison, and feature panel.
- Visual style: dark professional dashboard, restrained accents, clear status badges, animated chart reveal and card entrance.

## Error Handling
- Missing data/model errors return structured HTTP errors.
- Missing `GEMINI_API_KEY` or Gemini request failure returns an unavailable Gemini result without crashing the page.
- Frontend shows loading, unavailable, and error states explicitly.

## Testing
- Backend API tests verify metadata and prediction response shape using FastAPI `TestClient`.
- Existing Python tests continue to cover data loading, ground truth, modeling, and Gemini parsing.
- Frontend tests cover formatting and direction badge helpers.
- Build verification compiles React and Python modules.
