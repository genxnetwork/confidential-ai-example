DOCKER ?= docker
IMAGE ?= confidential-ai-example:local
GENXT_DEMO_CLIENT_WHEEL ?=
VENV ?= .venv
.PHONY: build test
build:
	install -d .image-wheel
	$(if $(GENXT_DEMO_CLIENT_WHEEL),cp "$(GENXT_DEMO_CLIENT_WHEEL)" ".image-wheel/$(notdir $(GENXT_DEMO_CLIENT_WHEEL))",@true)
	$(DOCKER) build --platform linux/amd64 --build-arg "GENXT_DEMO_CLIENT_WHEEL=$(if $(GENXT_DEMO_CLIENT_WHEEL),.image-wheel/$(notdir $(GENXT_DEMO_CLIENT_WHEEL)),)" -t "$(IMAGE)" .
test:
	$(VENV)/bin/python -m unittest discover -s tests -v
