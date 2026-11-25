FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY src ./src
COPY static ./static

RUN useradd --create-home searchflow
USER searchflow

EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')"
# Apply migrations, then serve. One worker, because crawl status is kept in memory.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn src.searchflow.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
