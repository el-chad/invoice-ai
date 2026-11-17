# Project guidance

## Architecture

- This is a Python 3.12+ application using FastAPI, Pydantic, PyMuPDF, and the OpenAI SDK. Dependencies and builds are managed with uv and `pyproject.toml`.
- Application code lives in `src/invoice_ai/`. `main.py` creates the FastAPI app and registers routers. The `invoice-ai` console script currently points to a placeholder function; use uvicorn to run the API.
- `api/` contains HTTP routes, `api/dependencies/` handles upload validation and HTTP error translation, and `api/errors/` contains API-specific errors. Keep routes thin.
- `schemas/` defines Pydantic request/response and invoice contracts. Use `Decimal` for monetary fields and preserve schema validation constraints.
- `services/` contains PDF and invoice extraction logic. Service errors live in `services/errors/`; keep HTTP concerns at the API boundary.
- The invoice extraction prompt currently lives in `api/prompts/invoice_extractor.md` and is loaded by the invoice extraction service. Treat prompt changes as behavior changes.
- `tests/` mirrors the API, service, and schema layers. `samples/` is available for sample documents; do not add private invoice data.

## Current data flow

- `POST /documents/preview` accepts a PDF upload. Upload validation checks the filename extension and enforces a 10 MB limit before PyMuPDF extracts text.
- The preview response includes the filename, page count, extracted text, and `requires_ocr`. Empty extracted text flags the need for OCR; OCR itself is not implemented.
- The separate invoice extraction service sends text to OpenAI and parses structured output into the `Invoice` schema. It currently uses `gpt-4o-mini` and is not connected to the preview route.
- Preserve explicit handling of empty input, missing output, refusals, incomplete responses, schema validation failures, and provider errors when modifying invoice extraction.

## Preferred development practices

- Make small, focused changes that follow the existing layered design. Avoid unrelated refactors or new abstractions without a concrete need.
- Use type hints and clear names. Put business logic in services, shared contracts in schemas, and HTTP status/error translation at the API boundary.
- Handle expected failures explicitly and preserve exception causes when translating errors. Avoid exposing internal error details in HTTP responses.
- Never commit credentials, API keys, or private documents. Avoid logging invoice contents or other sensitive payloads. Supply OpenAI credentials through the environment.
- Add or update meaningful tests when behavior changes. Mirror the source layer in the test directory, mock OpenAI calls, and generate PDF fixtures in memory or temporary directories. Routine tests must not require real API credentials or paid network calls.
- Use Ruff to format Python code consistently. Configuration lives in `pyproject.toml`: Python 3.12, an 88-character line target, double quotes, space indentation, and LF line endings. Let the formatter decide layout rather than formatting by hand.
- No linting workflow or type checker is currently configured. Do not introduce additional tooling as part of unrelated work.

## Development commands

- After completing a feature, run `uv run ruff format .`, verify with `uv run ruff format --check .`, and run `make test` before handing the work back. Report the results and any failures or checks that could not run. These checks are required even when no commit is requested.
- Install project and development dependencies: `uv sync`.
- Show available Make targets: `make help` (also the default for `make`).
- Run the API locally with auto-reload: `make run` (runs `uv run uvicorn invoice_ai.main:app --reload`).
- Run the entire test suite: `make test`. With no `TEST` provided, pytest uses the configured `tests/` directory.
- Run a test file: `make test TEST=tests/services/test_invoice_extractor.py`.
- Run an individual test: `make test TEST=tests/services/test_invoice_extractor.py::test_missing_parsed_output`. `TEST` accepts one pytest path or node ID, including parametrized test IDs; quote values containing shell-special characters.
- Format Python code: `uv run ruff format .`.
- Check formatting without changing files: `uv run ruff format --check .`. Run this check before committing Python changes; format changed files and rerun the check if it fails.
- Run relevant checks before committing. Report any failures or checks that could not run accurately; do not claim checks passed without running them. Documentation-only changes generally need a diff review rather than application tests.
- Keep dependency changes in `pyproject.toml` and `uv.lock` consistent.

## Commit guidelines

- Commit subjects must be **short and descriptive**. Follow the existing style, such as `feat: created invoice schemas`: a lowercase Conventional Commit prefix followed by a brief, concrete description. Past-tense descriptions fit the project's history.
- Use `feat`, `fix`, `refactor`, `test`, `docs`, or `chore` as appropriate. Scopes are optional; prefer the simple unscoped style used in existing commits unless a scope adds clarity.
- Examples:
  - `feat: added invoice extraction`
  - `fix: handled invalid PDFs`
  - `test: added upload validation tests`
  - `docs: added project guidelines`
- Keep each commit cohesive and stage only files intended for that change. Inspect the diff before committing.
- Preserve unrelated user changes. Never stage, commit, discard, or overwrite them as part of your task.
- Create a commit only when the user requests one.
