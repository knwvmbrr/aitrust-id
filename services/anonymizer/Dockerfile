FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY --chmod=0444 app.py healthcheck.py model_identity.py .
ENV PYTHONDONTWRITEBYTECODE=1
RUN python model_identity.py --seal && chmod 0444 model-manifest.json model-manifest.json.sha256
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
