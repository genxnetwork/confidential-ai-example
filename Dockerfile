# Users run the final image; the tests stage checks the application.
FROM python:3.15.2-slim-bookworm@sha256:498829c717b1e59fc42f0e7865eafe4e04ca0f70a3769d4ae70ba218df54507c AS runtime
ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    XDG_STATE_HOME=/state GENXT_DEMO_CALLBACK_BIND=0.0.0.0 \
    GENXT_DEMO_POLICY_DIR=/app/genoa-profiles
WORKDIR /app
COPY requirements.lock /app/
RUN python3 -m pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements.lock
COPY . /app/
ARG GENXT_DEMO_CLIENT_WHEEL=
RUN if [ -n "$GENXT_DEMO_CLIENT_WHEEL" ]; then \
        python3 scripts/install_client_wheel.py --client-wheel "$GENXT_DEMO_CLIENT_WHEEL"; \
    else python3 scripts/install_client_wheel.py; fi \
    && chmod 0644 /usr/local/confido-client-install.json \
    && rm -rf /app/.image-wheel
RUN python3 -c 'from demo.policy import prepare_genoa_profiles; prepare_genoa_profiles("/app/genoa-profiles")' \
    && useradd --create-home --uid 10001 demo \
    && install -d -m 0700 -o demo -g demo /state \
    && chown -R demo:demo /app/genoa-profiles
USER demo
CMD ["python3", "confai-promter.py"]

FROM runtime AS tests
COPY tests /app/tests
USER demo
RUN python3 -m unittest discover -s tests -v \
    && printf 'Application tests passed\n' > /tmp/application-tests-passed

FROM runtime AS final
# Make the final image depend on tests of this exact runtime and installed wheel.
COPY --from=tests /tmp/application-tests-passed /usr/local/share/confidential-ai-example/tests-passed
