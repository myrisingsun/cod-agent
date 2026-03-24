# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Проект

КОД-агент — система автоматического анализа залоговых договоров для банка. Извлекает 10 полей + Q&A через RAG. Агент НЕ принимает решений — автоматизирует рутину для кредитных аналитиков/юристов.

## Команды

```bash
# Запуск окружения
docker compose up -d
docker compose exec app alembic upgrade head
docker compose exec ollama ollama pull qwen2.5:7b

# Backend (внутри контейнера или с локальным venv)
pytest tests/unit/                          # unit тесты
pytest tests/integration/                   # интеграционные тесты
pytest tests/unit/test_foo.py::test_bar     # один тест
pytest --cov=app tests/unit/                # с покрытием
ruff check app/                             # линтинг
ruff format app/                            # форматирование

# Frontend (из папки frontend/)
npm install
npm run dev
npm run build
```

`asyncio_mode = "auto"` в `pyproject.toml` — декоратор `@pytest.mark.asyncio` не нужен.

## Архитектурный паттерн модулей

Каждый модуль (`parsing/`, `extraction/`, `llm/`, `pii/`, `rag/`, `storage/`) имеет три файла:
- `base.py` — `Protocol` с Pydantic-типами входа/выхода
- реализация(и) — классы, реализующие Protocol
- `factory.py` — возвращает нужную реализацию на основе `settings` (из `.env`)

Замена компонента = 1 новый файл + 1 строка в `.env`. Остальные модули не трогаются.

## Переключение Dev → Prod через .env

| Переменная | Dev | Prod |
|---|---|---|
| `LLM_BASE_URL` | `http://ollama:11434/v1` | vLLM endpoint |
| `PII_FILTER` | `noop` | `presidio` |
| `QUEUE_BACKEND` | `background_tasks` | `celery` |
| `PARSER_BACKEND` | `docling` | `docling` |

Все настройки — `app/config.py` (`pydantic-settings`, читает `.env`).

## Pipeline обработки документа

```
POST /packages (multipart PDF, JWT required)
  → MinIO (хранение) → PostgreSQL (status=RECEIVED)
  → background: process_package(package_id)
    1. Storage.get() → bytes
    2. Parser.parse() → ParsedDocument (Docling, fallback pdfplumber, timeout 30s)
    3. PIIFilter.filter() → очищенный текст
    4. RAG.index() → BGE-M3 → Qdrant (коллекция current_packages)
    5. RAG.retrieve() → few-shot из коллекции reference_templates
    6. Extractor.extract() → prompt + few-shot → LLM → JSON
    7. Pydantic validation + confidence scoring
    8. Save → PostgreSQL JSONB + audit_log
```

## 10 полей залогового договора

`contract_number`, `contract_date`, `pledgee`, `pledgor`, `pledgor_inn`, `pledge_subject`, `cadastral_number`, `area_sqm` (float), `pledge_value`, `validity_period` — все Optional в `PledgeFields` (`app/schemas/extraction.py`).

Confidence < 0.7 → строка подсвечивается жёлтым в UI.

## RAG

Две коллекции Qdrant:
- `reference_templates` — эталоны для few-shot при извлечении
- `current_packages` — чанки документов для Q&A чата

MVP: fixed-size chunking 400 токенов / 15% overlap, dense-only поиск.

## Auth

JWT: access token (30 мин, Bearer header) + refresh token (7 дней, httpOnly cookie). Все эндпоинты кроме `/auth/*` и `/health` требуют JWT. MVP: одна роль `analyst`. Зависимость инъекции — `app/auth/dependencies.py`.

## Текущее состояние реализации

Sprint 1 (скелет): реализованы заготовки модулей (`base.py` + `factory.py` для каждого модуля), `app/config.py`, `app/database.py`, `app/main.py` (только `/health`). Auth, models, pipeline, фронтенд — ещё не реализованы.

## Сервисы Docker Compose (dev)

| Сервис | Порт | Роль |
|---|---|---|
| app (FastAPI) | 8080 | Backend API |
| frontend (Vite) | 3000 | React SPA |
| postgres:15 | 5432 | Метаданные, users, audit |
| minio | 9000 / 9001 (console) | Файловое хранилище |
| qdrant | 6333 / 6334 (gRPC) | Векторная БД |
| ollama | 11434 | LLM inference (CPU) |
