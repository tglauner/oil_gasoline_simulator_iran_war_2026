# AGENTS.md (backend)

## Stack
- FastAPI app under `app/`
- Keep external market-fetch logic in `app/services/`
- Prefer standard library utilities over extra packages unless FastAPI itself requires them

## Local dev
- Create the venv in `backend/.venv`
- Run with `uvicorn app.main:app --reload`
- Keep tests in `backend/tests` and run them with `pytest`

## Conventions
- Put request/response models in `app/schemas.py` unless a larger split is justified.
- Keep env parsing centralized in `app/config.py`.
- Make parser failures degrade cleanly instead of crashing the API.
