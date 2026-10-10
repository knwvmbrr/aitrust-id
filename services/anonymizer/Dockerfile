FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
WORKDIR /app
COPY services/anonymizer/requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY --chmod=0444 services/anonymizer/app.py services/anonymizer/healthcheck.py services/anonymizer/model_identity.py .
ENV PYTHONDONTWRITEBYTECODE=1
RUN python model_identity.py --seal && chmod 0444 model-manifest.json model-manifest.json.sha256
COPY --chmod=0444 protocol/http_privacy.py ./protocol/
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "protocol.http_privacy:application", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
