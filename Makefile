.PHONY: all
all: build run

ARGS = $(filter-out $@,$(MAKECMDGOALS))

build:
	docker build --platform=linux/amd64 -t confidential-ai-example .

rebuild:
	docker build --platform=linux/amd64 --no-cache -t confidential-ai-example .

clean:
	docker rmi confidential-ai-example --force

cli:
	docker run --platform linux/amd64 --hostname genxt-confidential-ai -it confidential-ai-example /bin/bash

chat:
	docker run --platform linux/amd64 -it confidential-ai-example python3 confai-promter.py

%:
	@true

# Local development uses the sibling Confido checkout and an isolated Python environment.
PYTHON ?= python3
VENV ?= .venv
CONFIDO_LIB ?= ../confido/lib
MATURIN ?= $(VENV)/bin/maturin

.PHONY: dev-setup dev-update dev-chat dev-info

$(VENV)/bin/pip:
	$(PYTHON) -m venv $(VENV)

dev-setup: $(VENV)/bin/pip
	$(VENV)/bin/python -m pip install 'maturin>=1.6,<2' httpx openai
	$(MAKE) dev-update

dev-update: $(VENV)/bin/pip
	@test -f "$(CONFIDO_LIB)/Cargo.toml" || { echo "Confido checkout not found at $(CONFIDO_LIB); set CONFIDO_LIB=/path/to/confido/lib" >&2; exit 1; }
	@test -x "$(MATURIN)" || { echo "maturin not found at $(MATURIN); run make dev-setup or set MATURIN=/path/to/maturin" >&2; exit 1; }
	VIRTUAL_ENV="$(abspath $(VENV))" "$(MATURIN)" develop --release --manifest-path "$(abspath $(CONFIDO_LIB))/Cargo.toml"
	@$(MAKE) --no-print-directory dev-info

dev-info: $(VENV)/bin/pip
	@$(VENV)/bin/python scripts/dev_info.py "$(abspath $(CONFIDO_LIB))"

dev-chat: $(VENV)/bin/pip
	$(VENV)/bin/python confai-promter.py
