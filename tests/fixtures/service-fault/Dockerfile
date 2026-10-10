FROM docker.io/library/python:3.12-slim
WORKDIR /app
COPY --chmod=0444 app.py .
USER 10001:10001
CMD ["python", "app.py"]
