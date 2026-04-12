# kyrk-projekt — convenience targets.
#
# Usage:
#   make                 # same as `make help`
#   make test            # run the full test suite
#   make test-<service>  # e.g. make test-membership-service
#   make install         # pip install all service requirements
#   make lint            # python -m compileall + terraform fmt check
#   make bootstrap ENV=dev   # runs scripts/bootstrap.sh
#   make deploy ENV=dev      # triggers the deploy workflow via gh
#   make smoke ENV=dev       # curls /healthz on all six services
#   make clean           # remove __pycache__, .pytest_cache, etc.

SHELL := /bin/bash
PYTHON := python3
PIP := pip
SERVICES := membership-service membership-intake certificate-service activity-service reporting-service admin-web
ENV ?= dev

.PHONY: help install test test-% lint tf-validate bootstrap deploy smoke screenshots clean

help:
	@echo "kyrk-projekt — common targets"
	@echo
	@echo "  make install          install all service requirements (one venv)"
	@echo "  make test             run full test suite (Python + Node)"
	@echo "  make test-<service>   run tests for one service, e.g. test-admin-web"
	@echo "  make lint             python syntax check + terraform fmt"
	@echo "  make tf-validate      terraform init -backend=false + validate"
	@echo "  make bootstrap ENV=dev  run scripts/bootstrap.sh"
	@echo "  make deploy ENV=dev     trigger deploy.yml via gh CLI"
	@echo "  make smoke ENV=dev      curl /healthz on all six services"
	@echo "  make clean              remove build artifacts"
	@echo
	@echo "Services: $(SERVICES)"

install:
	@for svc in $(SERVICES); do \
	  echo "==> $$svc"; \
	  (cd services/$$svc && $(PIP) install -q -r requirements.txt); \
	done

test:
	@set -e; \
	for svc in $(SERVICES); do \
	  printf "==> %s\n" "$$svc"; \
	  (cd services/$$svc && $(PYTHON) -m pytest -q); \
	done
	@echo "==> wifi-intake-portal"
	@(cd frontend/wifi-intake-portal && node tests/test_content_decision.js)

test-%:
	@(cd services/$* && $(PYTHON) -m pytest -q)

lint:
	@$(PYTHON) -m compileall -q services automation/openclaw/import
	@if command -v terraform >/dev/null 2>&1; then \
	  (cd infra/terraform && terraform fmt -check -recursive); \
	else \
	  echo "terraform not installed — skipping fmt check"; \
	fi

tf-validate:
	@(cd infra/terraform && terraform init -backend=false && terraform validate)

bootstrap:
	@./scripts/bootstrap.sh $(ENV)

deploy:
	@command -v gh >/dev/null 2>&1 || { echo "gh CLI is required for 'make deploy'"; exit 1; }
	gh workflow run deploy.yml -f environment=$(ENV)
	@echo "Watching run…"
	gh run watch

smoke:
	@command -v gcloud >/dev/null 2>&1 || { echo "gcloud is required for 'make smoke'"; exit 1; }
	@REGION=$$(gh secret list --env $(ENV) 2>/dev/null | grep -q GCP_REGION && echo europe-north1 || echo europe-north1); \
	for svc in $(SERVICES); do \
	  URL=$$(gcloud run services describe $$svc --region=$$REGION --format='value(status.url)' 2>/dev/null); \
	  if [ -n "$$URL" ]; then \
	    CODE=$$(curl -s -o /dev/null -w "%{http_code}" "$$URL/healthz"); \
	    printf "%-22s %s (%s)\n" "$$svc" "$$CODE" "$$URL"; \
	  else \
	    printf "%-22s not deployed\n" "$$svc"; \
	  fi; \
	done

screenshots:
	@echo "See scripts/README.md for the Playwright screenshot harness."

clean:
	@find . -type d -name __pycache__ -prune -exec rm -rf {} \;
	@find . -type d -name .pytest_cache -prune -exec rm -rf {} \;
	@find . -type d -name .ruff_cache -prune -exec rm -rf {} \;
	@find . -type d -name "*.egg-info" -prune -exec rm -rf {} \;
	@echo "clean complete"
