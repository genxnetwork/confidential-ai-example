FROM ubuntu:22.04@sha256:2edbbc5dc405e9612ba3584ce95480277e3eb374407b5505fe26f17df77c7dbc
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 CONFIDO_RUNTIME_MODE=packaged
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates \
    && dpkg-query -W > /usr/local/share/runtime-packages.txt \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock /app/
COPY build/wheels /wheels
COPY build/wheel.sha256 /wheels/wheel.sha256
RUN cd /wheels && sha256sum -c wheel.sha256 \
    && python3 -m pip install --no-cache-dir --require-hashes -r /app/requirements.lock \
    && python3 -m pip install --no-index --no-deps /wheels/*.whl \
    && python3 -c 'import confido_verifier, _confai_transport; assert confido_verifier.__version__ == "0.2.0"' \
    && rm -rf /wheels
COPY confai-promter.py Makefile Dockerfile /app/
COPY build/runtime.json /app/build/runtime.json
COPY demo /app/demo
COPY profiles /app/profiles
COPY scripts /app/scripts
RUN python3 scripts/dev_info.py
RUN useradd --create-home --uid 10001 demo
USER demo
CMD ["python3", "confai-promter.py"]
