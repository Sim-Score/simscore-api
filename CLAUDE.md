# SimScore API Dev Guide

## Commands
- **Setup:** `poetry install --no-root && poetry shell`
- **Local Dev:** `supabase start && fastapi dev`
- **Tests:** 
  - All: `pytest tests/`
  - Single file: `pytest tests/api/v1/routes/test_ideas.py`
  - Single test: `pytest tests/api/v1/routes/test_ideas.py::test_function_name`
- **Lint/Format:** `black app/ tests/`
- **Type Check:** `mypy app/ tests/`

## Code Style
- **Imports:** stdlib → third-party → project (alphabetically within groups)
- **Naming:** `snake_case` for variables/functions, `PascalCase` for classes, `UPPER_CASE` for constants
- **Types:** Use type annotations for all function parameters and return values
- **Error Handling:** Use FastAPI `HTTPException` with appropriate status codes
- **Documentation:** Google-style docstrings with triple double-quotes
- **Architecture:** Follow FastAPI patterns with routes, models, services separation
- **Formatting:** Project uses Black with default settings

## Environment
This project uses Poetry for dependency management and FastAPI for the API framework.