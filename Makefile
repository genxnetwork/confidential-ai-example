PYTHON ?= python3
VENV ?= .venv
CONFIDO_LIB ?= ../confido/lib
MATURIN ?= $(abspath $(VENV))/bin/maturin
DOCKER ?= docker
IMAGE ?= confidential-ai-example:0.2.0
.PHONY: dev-setup dev-update dev-chat dev-info wheel build chat test
$(VENV)/bin/pip:
	$(PYTHON) -m venv $(VENV)
dev-setup: $(VENV)/bin/pip
	$(VENV)/bin/python -m pip install 'maturin==1.15.0' 'patchelf==0.17.2.4'
	$(VENV)/bin/python -m pip install --require-hashes -r requirements.lock
	$(MAKE) dev-update
$(VENV)/bin/maturin: | $(VENV)/bin/pip
	$(VENV)/bin/python -m pip install 'maturin==1.15.0' 'patchelf==0.17.2.4'
wheel: $(VENV)/bin/maturin
	$(VENV)/bin/python scripts/build_wheels.py --confido-lib $(abspath $(CONFIDO_LIB)) --maturin $(MATURIN)
dev-update: wheel
	$(VENV)/bin/python scripts/install_wheels.py
	$(MAKE) dev-info
dev-info:
	$(VENV)/bin/python scripts/dev_info.py $(abspath $(CONFIDO_LIB))
dev-chat:
	$(VENV)/bin/python scripts/ensure_runtime.py $(abspath $(CONFIDO_LIB))
	CONFIDO_COLOR=$${CONFIDO_COLOR:-always} $(VENV)/bin/python confai-promter.py
build: dev-update
	$(DOCKER) build --platform linux/amd64 -t $(IMAGE) .
	$(VENV)/bin/python scripts/build_manifest.py $(DOCKER) $(IMAGE)
chat:
	$(DOCKER) run --rm --platform linux/amd64 -it --env CONFIDO_COLOR=$${CONFIDO_COLOR:-always} $(IMAGE)
test:
	$(VENV)/bin/python -m unittest discover -s tests -v
	cargo test --locked --manifest-path native_transport/Cargo.toml
