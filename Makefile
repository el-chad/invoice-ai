.DEFAULT_GOAL := help

TEST ?=

.PHONY: help run test

help:
	@echo 'make run                       Start the local API with auto-reload'
	@echo 'make test                      Run all tests'
	@echo 'make test TEST=path/to/test.py  Run a test file'
	@echo 'make test TEST=path/to/test.py::test_name  Run a specific test'

run:
	uv run uvicorn invoice_ai.main:app --reload

test:
	uv run pytest $(if $(strip $(TEST)),"$(TEST)")
