FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170
WORKDIR /app
COPY services/gateway/requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY --chmod=0444 services/gateway/app.py services/gateway/healthcheck.py .
COPY --chmod=0444 protocol/http_privacy.py protocol/normalization.py protocol/replay_identity.py protocol/transport_signing.py protocol/unicode15-data.json ./protocol/
RUN python -c "import os, stat; print('protocol directory mode before correction: %04o' % stat.S_IMODE(os.stat('/app/protocol').st_mode))"
RUN chmod 0555 /app/protocol
USER 10001:10001
RUN python -c "import importlib.util; assert importlib.util.find_spec('protocol.http_privacy').origin == '/app/protocol/http_privacy.py'"
EXPOSE 8000
CMD ["uvicorn", "protocol.http_privacy:application", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
