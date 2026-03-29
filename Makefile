.PHONY: test test-mac test-nt


test-mac:
	@clear
	@echo Running test suite...
	@uv run -m pytest tests/ -q

test-nt:
	@cmd /c cls
	@echo Running test suite...
	@uv run -m pytest tests/ -q


ifeq ($(OS),Windows_NT)
test: test-nt
else
test: test-mac
endif
