FROM python:3.12-slim

WORKDIR /app

# The `cryptography` wheel's vendored OpenSSL misdetects ARM crypto
# extensions under some Apple Silicon Docker Desktop virtualization setups
# (observed as SIGILL / "Illegal instruction" on import). Disabling ARM
# crypto instruction usage in that vendored OpenSSL avoids the crash; the
# container's system OpenSSL (used by stdlib ssl/hashlib) is unaffected.
ENV OPENSSL_armcap=0

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -c requirements.txt ".[test,lint]"

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
