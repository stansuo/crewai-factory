.PHONY: run demo test lint typecheck ci clean docker-run docker-build

# ── Run locally ──────────────────────────────────────────────────

run:
	uv run python -m crewai_factory

demo:
	@echo "Running demo with tech-blogger persona..."
	uv run python -m crewai_factory --persona personas/tech-blogger.yaml

# ── Quality ──────────────────────────────────────────────────────

test:
	uv run pytest

test-cov:
	uv run pytest --cov=crewai_factory --cov-report=term-missing

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

typecheck:
	uv run mypy src/

ci: lint typecheck test

# ── Docker ───────────────────────────────────────────────────────

docker-build:
	docker compose build

docker-run:
	docker compose run --rm crewai-factory

# ── Housekeeping ─────────────────────────────────────────────────

clean:
	rm -rf output/*.md .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
