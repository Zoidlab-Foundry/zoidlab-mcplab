# MCPLab backend image. Runs the FastAPI API by default; the same image runs the Celery
# worker by overriding the command:
#   docker run ... celery -A celery_app worker --loglevel=info --concurrency=4
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8706
EXPOSE 8706
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8706}"]
