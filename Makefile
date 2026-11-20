PYTHON ?= $(shell command -v python3.12 || command -v python3.11 || command -v python3.13 || command -v python3)
ENV_PY = .venv/bin/python
ROLE ?= coverage
PORT ?= 8000

.PHONY: setup deps seed build run dev-console doctor brane-check logins login test evidence reset

setup: deps
	$(ENV_PY) -m backend.demo setup
	$(MAKE) build
	$(MAKE) doctor

deps: .venv/bin/python
	$(ENV_PY) -m pip install --disable-pip-version-check -r requirements-dev.txt
	npm ci --prefix console --no-audit --no-fund

.venv/bin/python:
	$(PYTHON) -c 'import sys; sys.exit("Python 3.11+ required") if sys.version_info < (3, 11) else sys.exit(0)'
	$(PYTHON) -m venv .venv

seed:
	$(ENV_PY) -m backend.demo setup

build:
	npm run build --prefix console

run:
	CLEARANCE_DEMO_LOGIN=1 $(ENV_PY) -m uvicorn backend.main:app --no-proxy-headers --host 127.0.0.1 --port $(PORT)

dev-console:
	npm run dev --prefix console

doctor:
	$(ENV_PY) -m backend.demo doctor

brane-check:
	$(ENV_PY) -m backend.demo doctor --brane

logins:
	@$(ENV_PY) -m backend.demo logins

login:
	@$(ENV_PY) -m backend.demo login $(ROLE)

test:
	$(ENV_PY) -m pytest -q

evidence:
	$(ENV_PY) -m tools.workflow_evidence --output .clearance/evidence/workflow-fixture.csv

reset:
	$(ENV_PY) -m backend.demo reset
