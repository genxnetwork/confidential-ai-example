PYTHON ?= python3
VENV ?= .venv
MATURIN ?= $(abspath $(VENV))/bin/maturin
CONFIDO_WHEEL ?=
DOCKER ?= docker
IMAGE ?= confidential-ai-example:0.2.0
GENOA_PROFILES ?= .artifacts/genoa-console-profiles
.PHONY: dev-setup dev-update dev-chat dev-chat-genoa dev-info wheel build chat test
$(VENV)/bin/pip:
	$(PYTHON) -m venv $(VENV)
dev-setup: $(VENV)/bin/pip
	$(VENV)/bin/python -m pip install 'maturin==1.15.0' 'patchelf==0.17.2.4'
	$(VENV)/bin/python -m pip install --require-hashes -r requirements.lock
	$(MAKE) dev-update
$(VENV)/bin/maturin: | $(VENV)/bin/pip
	$(VENV)/bin/python -m pip install 'maturin==1.15.0' 'patchelf==0.17.2.4'
wheel: $(VENV)/bin/maturin
	$(VENV)/bin/python scripts/build_wheels.py --maturin "$(MATURIN)" $(if $(CONFIDO_WHEEL),--verifier-wheel "$(CONFIDO_WHEEL)",)
dev-update: wheel
	$(VENV)/bin/python scripts/install_wheels.py
	$(MAKE) dev-info
dev-info:
	$(VENV)/bin/python scripts/dev_info.py
dev-chat:
	$(VENV)/bin/python scripts/ensure_runtime.py
	CONFIDO_COLOR=$${CONFIDO_COLOR:-always} $(VENV)/bin/python confai-promter.py
dev-chat-genoa:
	install -d -m 0700 "$(GENOA_PROFILES)"
	install -m 0600 profiles/match.json "$(GENOA_PROFILES)/match.json"
	install -m 0600 profiles/mismatch.json "$(GENOA_PROFILES)/mismatch.json"
	install -m 0600 profiles/verifier-genoa-stage-registry.json "$(GENOA_PROFILES)/verifier-match.json"
	install -m 0600 profiles/verifier-genoa-stage-mismatch.json "$(GENOA_PROFILES)/verifier-mismatch.json"
	CONFIDO_POLICY_DIR="$(abspath $(GENOA_PROFILES))" $(MAKE) dev-chat
build: dev-update
	$(DOCKER) build --platform linux/amd64 -t $(IMAGE) .
	$(VENV)/bin/python scripts/build_manifest.py $(DOCKER) $(IMAGE)
chat:
	$(DOCKER) run --rm --platform linux/amd64 -it --env CONFIDO_COLOR=$${CONFIDO_COLOR:-always} $(IMAGE)
test:
	$(VENV)/bin/python -m unittest discover -s tests -v
	cargo test --locked --manifest-path native_transport/Cargo.toml
