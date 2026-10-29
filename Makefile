# Run `make` to list the targets.

.DEFAULT_GOAL := help
.PHONY: help install upgrade serve build check clean

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'

install: ## Create .venv from uv.lock
	uv sync

upgrade: ## Update Python packages to the newest allowed versions (rewrites uv.lock)
	uv lock --upgrade
	uv sync

serve: ## Preview the site at http://127.0.0.1:8000 with live reload
	uv run mkdocs serve

build: ## Build the site into site/, failing on warnings like CI does
	uv run mkdocs build --strict

check: build ## Everything CI checks before deploying

clean: ## Remove the built site
	rm -rf site
