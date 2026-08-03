FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[test]"

COPY app ./app
COPY static ./static
COPY templates ./templates
COPY migrations ./migrations
COPY alembic.ini ./
COPY entrypoint.sh ./
COPY tests ./tests

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
