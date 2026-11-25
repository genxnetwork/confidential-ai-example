PYTHON ?= python3
VENV ?= .venv
CONFIDO_ROOT := $(abspath .artifacts/confido-src)
CONFIDO_LIB := $(CONFIDO_ROOT)/lib
MATURIN ?= $(abspath $(VENV))/bin/maturin
DOCKER ?= docker
IMAGE ?= confidential-ai-example:0.2.0
GENOA_PROFILES ?= .artifacts/genoa-console-profiles
.PHONY: confido-source dev-setup dev-update dev-chat dev-chat-genoa dev-info wheel build chat test
confido-source:
	$(PYTHON) scripts/fetch_confido.py --directory "$(CONFIDO_ROOT)"
$(VENV)/bin/pip:
	$(PYTHON) -m venv $(VENV)
dev-setup: $(VENV)/bin/pip
	$(VENV)/bin/python -m pip install 'maturin==1.15.0' 'patchelf==0.17.2.4'
	$(VENV)/bin/python -m pip install --require-hashes -r requirements.lock
	$(MAKE) dev-update
$(VENV)/bin/maturin: | $(VENV)/bin/pip
	$(VENV)/bin/python -m pip install 'maturin==1.15.0' 'patchelf==0.17.2.4'
wheel: $(VENV)/bin/maturin confido-source
	$(VENV)/bin/python scripts/build_wheels.py --confido-lib "$(CONFIDO_LIB)" --maturin "$(MATURIN)"
dev-update: wheel
	$(VENV)/bin/python scripts/install_wheels.py
	$(MAKE) dev-info
dev-info: confido-source
	$(VENV)/bin/python scripts/dev_info.py "$(CONFIDO_LIB)"
dev-chat: confido-source
	$(VENV)/bin/python scripts/ensure_runtime.py "$(CONFIDO_LIB)"
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
	$(DOCKER) run --rm --platform linux/amd64 -it -p 127.0.0.1:8765:8765 \
		--env CONFIDO_COLOR=$${CONFIDO_COLOR:-always} \
		--env CONFIDO_AUTH_CALLBACK_BIND=0.0.0.0 $(IMAGE)
test:
	$(VENV)/bin/python -m unittest discover -s tests -v
	cargo test --locked --manifest-path native_transport/Cargo.toml
