FROM ubuntu:22.04@sha256:2edbbc5dc405e9612ba3584ce95480277e3eb374407b5505fe26f17df77c7dbc
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates libtss2-tctildr0 \
    && dpkg-query -W > /usr/local/share/runtime-packages.txt \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock /app/
COPY build/wheels /wheels
COPY build/wheel.sha256 /wheels/wheel.sha256
RUN cd /wheels && sha256sum -c wheel.sha256 \
    && python3 -m pip install --no-cache-dir --require-hashes -r /app/requirements.lock \
    && python3 -m pip install --no-index --no-deps /wheels/confido_atls-0.3.0-*.whl \
    && python3 -c 'import confido; assert confido.__version__ == "0.3.0"' \
    && rm -rf /wheels
COPY confai-promter.py /app/
COPY profiles /app/profiles
COPY scripts /app/scripts
RUN useradd --create-home --uid 10001 demo
USER demo
CMD ["python3", "confai-promter.py"]
