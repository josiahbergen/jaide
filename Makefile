.PHONY: clear test

ifeq ($(OS),Windows_NT)
CLEAR = cmd /c cls
else
CLEAR = clear
endif

clear:
	@$(CLEAR)

test: clear
	@uv run -m pytest tests/ -q
