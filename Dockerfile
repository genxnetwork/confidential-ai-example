FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y --no-install-recommends libtss2-dev python3-pip
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install confido-atls==0.0.6 httpx openai 

RUN useradd -m -d /user -s /bin/bash user   
WORKDIR /user
COPY ./confai-promter.py /user
USER user
CMD ["bash"]
