PYTHON ?= python3
ENV_FILE ?= $(HOME)/.config/aitrust-id/runtime.env
COMPOSE = docker compose --env-file "$(ENV_FILE)" -f deploy/docker-compose.yml
.PHONY: init check doctor build verify verify-runtime test regressions gates up down deploy
init:
	$(PYTHON) scripts/aitrust.py init --env-file "$(ENV_FILE)"
check:
	$(PYTHON) scripts/aitrust.py check --env-file "$(ENV_FILE)"
doctor:
	$(PYTHON) scripts/aitrust.py doctor --env-file "$(ENV_FILE)"
build: verify-changelog
	$(COMPOSE) build
up:
	$(COMPOSE) up -d --wait --wait-timeout 60
down:
	$(COMPOSE) down
test:
	$(PYTHON) -m pytest tests -q
.PHONY: verify-ps verify-device
verify-ps:
	$(PYTHON) scripts/verify-ps.py
verify-device: site-build
	AITRUST_VERIFY_PYTHON="$(PYTHON)" npm run verify:device
verify: verify-changelog test
	npm run verify:browser
verify-runtime:
	$(PYTHON) scripts/verify-runtime.py --env-file "$(ENV_FILE)"
	AITRUST_ENV_FILE="$(ENV_FILE)" node scripts/verify-extension.cjs
regressions:
	$(PYTHON) scripts/verify-regressions.py --output eval/regression-report.json
gates:
	$(PYTHON) eval/harness.py --fixtures eval/datasets/unsafe_code/ps_v1.jsonl --output eval/report.json
deploy: build up

.PHONY: site-build site-verify site-deploy
site-build:
	npm run build:site
site-verify: verify-changelog
	npm run verify:enterprise
	npm run verify:site
	npm run verify:approachability
site-deploy: site-build
	npm run deploy:site

.PHONY: host-build host-verify host-deploy
host-build: verify-changelog
	bash -n deploy/host/bootstrap.sh deploy/host/deploy.sh deploy/host/verify.sh
	$(PYTHON) -m py_compile deploy/host/verify.py
host-verify:
	bash deploy/host/verify.sh
host-deploy: host-build
	bash deploy/host/deploy.sh

.PHONY: backup-build backup-deploy backup-configure backup-verify
backup-build: verify-changelog
	bash -n deploy/backup/bootstrap.sh deploy/backup/deploy.sh deploy/backup/verify.sh deploy/backup/schedule.sh deploy/backup/source-monitor.sh
	$(PYTHON) -m py_compile deploy/backup/remote.py deploy/backup/cycle.py deploy/backup/verify.py deploy/backup/configure.py deploy/backup/restore.py deploy/backup/negative-checks.py deploy/backup/source-health.py
	$(PYTHON) -m unittest discover -s tests -p test_backup_protocol.py -v
backup-deploy: backup-build
	bash deploy/backup/deploy.sh
backup-configure: backup-build
	$(PYTHON) deploy/backup/configure.py
backup-verify:
	bash deploy/backup/verify.sh

.PHONY: alerts-build
alerts-build: verify-changelog
	bash -n deploy/alerts/install.sh
	$(PYTHON) -m py_compile deploy/alerts/alerts.py
	$(PYTHON) -m unittest discover -s tests -p test_operational_alerts.py -v

.PHONY: notifications-build
notifications-build: verify-changelog
	bash -n deploy/notifications/install.sh deploy/notifications/prepare-edge.sh deploy/notifications/activate-edge.sh
	$(PYTHON) -m py_compile deploy/notifications/provision.py deploy/notifications/verify-local.py

.PHONY: scope-render verify-scope
scope-render:
	$(PYTHON) scripts/render-scope-plan.py
verify-scope:
	$(PYTHON) scripts/verify-scope-plan.py

.PHONY: progress-render verify-progress
progress-render:
	$(PYTHON) scripts/scope-progress.py --render
verify-progress:
	$(PYTHON) scripts/scope-progress.py
	$(PYTHON) scripts/verify-accountability.py
	$(PYTHON) scripts/verify-vocabulary.py

.PHONY: performance-build performance-verify
performance-build: verify-changelog
	$(PYTHON) scripts/build-tag-performance.py
performance-verify:
	npm run verify:performance

.PHONY: verify-changelog hooks-install
verify-changelog:
	$(PYTHON) scripts/verify-changelog.py
hooks-install:
	git config --local core.hooksPath .githooks
