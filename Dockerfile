FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libtss2-dev \
        python3-pip \
        software-properties-common \
        && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install confido-atls==0.1.2 httpx openai --index-url=https://pypi.org/simple

RUN useradd -m -d /user -s /bin/bash user   
WORKDIR /user
COPY ./confai-promter.py /user
USER user
CMD ["bash"]
