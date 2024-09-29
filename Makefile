.PHONY: all
all: build run

ARGS = $(filter-out $@,$(MAKECMDGOALS))

build:
	docker build -t confidential-ai-example .

rebuild:
	docker build --no-cache -t confidential-ai-example .

cli:
	docker run --platform linux/amd64 --hostname genxt-confidential-ai -it confidential-ai-example /bin/bash

promt:
	docker run --platform linux/amd64 -it confidential-ai-example python3 confai-promter.py $(ARGS)

%:
	@true
