FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170
WORKDIR /app
COPY services/evaluator/requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY --chmod=0444 services/evaluator/app.py services/evaluator/healthcheck.py .
COPY --chmod=0444 protocol/http_privacy.py ./protocol/
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "protocol.http_privacy:application", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
