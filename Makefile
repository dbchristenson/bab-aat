.PHONY: run install clean check runner
.DEFAULT_GOAL:=runner

run: install
	uv run python manage.py runserver

install: pyproject.toml
	uv sync

clean:
	rm -rf `find . -type d -name __pycache__`
	rm -rf .ruff_cache

check:
	uv run flake8 .

runner: check run clean