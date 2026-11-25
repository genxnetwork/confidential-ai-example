DOCKER ?= docker
IMAGE ?= confidential-ai-example:local
CONFIDO_CLIENT_WHEEL ?=
VENV ?= .venv
.PHONY: build test
build:
	install -d .image-wheel
	$(if $(CONFIDO_CLIENT_WHEEL),cp "$(CONFIDO_CLIENT_WHEEL)" ".image-wheel/$(notdir $(CONFIDO_CLIENT_WHEEL))",@true)
	$(DOCKER) build --platform linux/amd64 --build-arg "CONFIDO_CLIENT_WHEEL=$(if $(CONFIDO_CLIENT_WHEEL),.image-wheel/$(notdir $(CONFIDO_CLIENT_WHEEL)),)" -t "$(IMAGE)" .
test:
	$(VENV)/bin/python -m unittest discover -s tests -v
