FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
# Install base + dev deps only; heavy ML groups (parsing, rag, pii) added per sprint
ARG EXTRA_GROUPS="dev"
RUN pip install --no-cache-dir -e ".[$EXTRA_GROUPS]"

COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
