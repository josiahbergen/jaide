.PHONY: test test-unix test-nt


test-unix:
	@clear
	@echo Running test suite...
	@uv run -m pytest -q

test-nt:
	@echo Running test suite...
	@uv run -m pytest -q


ifeq ($(OS),Windows_NT)
test: test-nt
else
test: test-unix
endif
