# Local Dev Fixes — без Docker для app

## Что изменено

### Конфигурация

- **`app/config.py`** — поддержка `ENV_FILE` env var: `ENV_FILE=.env.local` переключает все URL с Docker-хостнеймов на `localhost`
- **`.env.local`** — конфиг для локального запуска (localhost URLs, `PARSER_BACKEND=pdfplumber`, `LLM_TIMEOUT=600`)
- **`pyproject.toml`** — `qdrant-client>=1.17.0` (совместимость с сервером 1.17.x); добавлен `[tool.setuptools.packages.find]`

### Docker

- **`docker-compose.yml`** — Ollama получает GPU через `deploy.resources.reservations` (Quadro P2000, CUDA 6.1)
- **`frontend/vite.config.ts`** — прокси читает `VITE_BACKEND_URL` env var (по умолчанию `localhost:8080`), добавлен `changeOrigin: true`

### Backend

- **`app/pipeline/process_package.py`** — background task создаёт собственную `AsyncSession` вместо повторного использования сессии запроса (та закрывается до завершения задачи)
- **`app/api/routes_packages.py`**, **`routes_extraction.py`** — убрана передача `db` в `process_package()`
- **`app/rag/qdrant_retriever.py`** — `client.search()` → `client.query_points()` (API qdrant-client 1.17.x), результат через `.points`

### Frontend

- **`frontend/src/api/client.ts`** — исправлен interceptor: при неудаче refresh все ожидающие запросы в `_refreshQueue` теперь отклоняются (`reject`), а не зависают навсегда
- **`frontend/src/context/AuthContext.tsx`** — добавлен `cancelled` flag в `useEffect` для корректной работы с React StrictMode (двойной вызов эффектов в dev-режиме)

## Запуск локально

```bash
# Инфраструктура (postgres, minio, qdrant, ollama) — в Docker
docker compose up -d postgres minio qdrant ollama

# Backend
bash scripts/start_backend.sh   # ENV_FILE=.env.local, порт 8081

# Frontend
bash scripts/start_frontend.sh  # VITE_BACKEND_URL=http://localhost:8081, порт 3000
```

## Скрипты

| Файл | Назначение |
|---|---|
| `scripts/start_backend.sh` | Запуск uvicorn с `.env.local` на порту 8081 |
| `scripts/start_frontend.sh` | Запуск Vite dev server с прокси на 8081 |
| `scripts/kill_backend.sh` | Остановка локального backend |
