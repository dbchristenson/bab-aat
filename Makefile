.PHONY: run install clean check runner update
.DEFAULT_GOAL:=runner

run: install
	docker compose up --build

update:
	git pull

install: pyproject.toml
	uv sync

clean:
	rm -rf `find . -type d -name __pycache__`
	rm -rf .DS_store

runner: update install clean run