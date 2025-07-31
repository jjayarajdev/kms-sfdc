# KMS-SFDC Vector Database Makefile

.PHONY: help install test lint format clean build-index run-api setup-env

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run tests with coverage"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code with black"
	@echo "  clean       - Clean up generated files"
	@echo "  setup-env   - Set up development environment"
	@echo "  build-index - Build FAISS index from SFDC data"
	@echo "  run-api     - Run the search API server"

# UV Installation check
check-uv:
	@which uv > /dev/null || (echo "UV not found. Installing UV..." && curl -LsSf https://astral.sh/uv/install.sh | sh)

# Installation with UV
install: check-uv
	uv sync

# Development environment setup with UV
setup-env: check-uv
	uv sync --dev
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "Created .env from .env.example"; \
		else \
			echo ".env file already exists or no .env.example found"; \
		fi \
	fi
	mkdir -p data logs
	@echo "Environment setup complete. Please edit .env with your SFDC credentials if needed."

# Legacy pip support (fallback)
install-pip:
	pip install -r requirements.txt

# Testing with UV
test: check-uv
	uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

test-unit: check-uv
	uv run pytest tests/ -v -m "not integration"

test-integration: check-uv
	uv run pytest tests/ -v -m integration

# Code quality with UV
lint: check-uv
	uv run flake8 src/ tests/
	uv run mypy src/

format: check-uv
	uv run black src/ tests/ scripts/
	@echo "Code formatting complete"

# Clean up
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf data/faiss_index.bin
	rm -rf data/case_metadata.json
	rm -rf logs/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Application commands with UV
build-index: check-uv
	uv run python scripts/build_index.py

build-index-sample: check-uv
	uv run python scripts/build_index.py --max-records 1000

# Build with mock data (no SFDC connection required)
build-index-mock: check-uv
	uv run python scripts/build_index_mock.py

# Build with small real SFDC dataset (50 cases for testing)
build-index-small: check-uv
	uv run python scripts/build_index_small.py

run-api: check-uv
	uv run python scripts/run_api.py

# Development mode API (with reload)
run-api-dev: check-uv
	uv run uvicorn src.search.api:app --host 0.0.0.0 --port 8008 --reload

# Docker commands (if Docker is used)
docker-build:
	docker build -t kms-sfdc-vector-db .

docker-run:
	docker run -p 8000:8000 --env-file .env kms-sfdc-vector-db

# CI/CD helpers
check: lint test
	@echo "All checks passed!"

# Nomic setup with UV
setup-nomic: check-uv
	uv run python scripts/setup_nomic.py

# Test local embeddings with UV
test-embeddings: check-uv
	uv run python -c "from src.vectorization.vector_db import VectorDatabase; vdb = VectorDatabase(); print('Testing embeddings...'); emb = vdb.create_embeddings(['test case']); print(f'Success! Embedding shape: {emb.shape}')"

# Production scale testing with UV
test-large-scale: check-uv
	@echo "=== Testing Large Scale Configuration ==="
	uv run python -c "from src.vectorization import VectorDatabase; vdb = VectorDatabase(); print('Large scale config:'); import json; print(json.dumps(vdb.config.__dict__, indent=2, default=str))"

# Monitor index health for large scale with UV
monitor-index-health: check-uv
	uv run python -c "from src.vectorization import VectorDatabase; vdb = VectorDatabase(); vdb.load_index(); metrics = vdb.get_index_health_metrics(); import json; print('Index Health:'); print(json.dumps(metrics, indent=2))"

# Cognate AI Integration with UV
test-cognate-integration: check-uv
	uv run python scripts/cognate_ai_integration.py

# GSR milestone demonstrations with UV
demo-field-finalization: check-uv
	@echo "=== Milestone 1: Field Finalization Demo ==="
	uv run python -c "from src.data_extraction import SFDCClient; client = SFDCClient(); print('Available fields:'); import json; print(json.dumps(client.get_case_fields_info(), indent=2))"

demo-initial-vectorization: check-uv
	@echo "=== Milestone 2: Initial Vectorization Demo ==="
	make build-index-sample
	uv run python -c "from src.vectorization import VectorDatabase; vdb = VectorDatabase(); vdb.load_index(); print(f'Vectorized {vdb.get_stats()[\"total_vectors\"]} cases')"

demo-accuracy-measurement: check-uv
	@echo "=== Milestone 4: Accuracy Measurement Demo ==="
	uv run python -c "from src.vectorization import VectorDatabase; vdb = VectorDatabase(); vdb.load_index(); results = vdb.search('unexpected reboots', top_k=5); print(f'Test search returned {len(results)} results with avg similarity: {sum(r[\"similarity_score\"] for r in results)/len(results) if results else 0:.3f}')"

# Display configuration with UV
show-config: check-uv
	uv run python -c "from src.utils.config import config; import json; print(json.dumps(config.dict(), indent=2, default=str))"

# Admin UI commands
admin-ui-install:
	cd admin-ui && npm install

admin-ui-dev:
	cd admin-ui && npm run dev

admin-ui-build:
	cd admin-ui && npm run build

admin-ui-start: admin-ui-install
	cd admin-ui && npm run dev

# Start both API and Admin UI
start-all: 
	@echo "Starting KMS-SFDC API server and Admin UI..."
	@make run-api & make admin-ui-dev