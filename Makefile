PYTHON ?= python3
VENV ?= .venv
CONFIDO_LIB ?= ../confido/lib
MATURIN ?= $(abspath $(VENV))/bin/maturin
DOCKER ?= docker
IMAGE ?= confidential-ai-example:0.3.0

.PHONY: dev-setup dev-update dev-chat dev-info wheel build chat test
$(VENV)/bin/pip:
	$(PYTHON) -m venv $(VENV)

dev-setup: $(VENV)/bin/pip
	$(VENV)/bin/python -m pip install 'maturin==1.15.0' 'patchelf==0.17.2.4'
	$(VENV)/bin/python -m pip install --require-hashes -r requirements.lock
	$(MAKE) dev-update

$(VENV)/bin/maturin: $(VENV)/bin/pip
	$(VENV)/bin/python -m pip install 'maturin==1.15.0' 'patchelf==0.17.2.4'

wheel: $(VENV)/bin/maturin
	$(MAKE) -C $(CONFIDO_LIB) wheel MATURIN=$(MATURIN) PYTHON=$(abspath $(VENV))/bin/python
	mkdir -p build/wheels
	rm -f build/wheels/confido_atls-*.whl
	cp $(CONFIDO_LIB)/target/wheels/confido_atls-0.3.0-*.whl build/wheels/
	cd build/wheels && sha256sum confido_atls-0.3.0-*.whl > ../wheel.sha256

dev-update: wheel
	$(VENV)/bin/python -m pip install --force-reinstall --no-index --no-deps build/wheels/confido_atls-0.3.0-*.whl
	$(MAKE) dev-info

dev-info:
	$(VENV)/bin/python scripts/dev_info.py $(abspath $(CONFIDO_LIB))

dev-chat:
	$(VENV)/bin/python confai-promter.py

build: dev-update
	$(DOCKER) build --platform linux/amd64 -t $(IMAGE) .
	$(VENV)/bin/python scripts/build_manifest.py $(DOCKER)

chat:
	$(DOCKER) run --rm --platform linux/amd64 -it --env CONFIDO_USERNAME --env CONFIDO_PASSWORD $(IMAGE)

test:
	$(VENV)/bin/python -m unittest discover -s tests -v
