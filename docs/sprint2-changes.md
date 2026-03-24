# Sprint 2 — Storage + Parsing

## Что реализовано

### Storage модуль (`app/storage/`)
- `s3_storage.py` — `S3Storage`: загрузка, получение, удаление файлов через boto3.
  Совместим с MinIO (dev) и AWS S3 (prod). Автоматически создаёт bucket при первом запуске.
  Ключ хранения: `{package_id}/{filename}`.

### Parsing модуль (`app/parsing/`)
- `pdfplumber_parser.py` — `PdfPlumberParser`: быстрый sync-парсер, обёрнут в async.
  Всегда доступен (входит в группу `storage`).
- `docling_parser.py` — `DoclingParser`: высокоточный парсер, запускается в thread executor.
  Таймаут 30 секунд. Требует группу `parsing` (`docling>=2.10.0`).
  Активируется через `PARSER_BACKEND=docling` в `.env`.

### Packages API (`app/api/routes_packages.py`)
| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/packages` | Загрузка PDF (multipart), сохранение в MinIO + PostgreSQL, запуск pipeline |
| `GET` | `/packages` | Список пакетов текущего пользователя |
| `GET` | `/packages/{id}` | Статус и метаданные пакета |
| `DELETE` | `/packages/{id}` | Удаление из MinIO + БД |

Все эндпоинты требуют JWT (Bearer). Лимит файла: 50 МБ. Принимаются только `.pdf`.

### Background pipeline (`app/pipeline/process_package.py`)
Шаги, реализованные в Sprint 2:
1. `Storage.get()` — загрузка байтов из MinIO
2. `Parser.parse()` → `ParsedDocument` (text, pages, metadata)
3. Обновление статуса в БД: `RECEIVED → PROCESSING → PARSED`

Шаги 4–8 (PII, RAG, LLM) — заглушки, реализуются в Sprint 3–5.

### Docker / зависимости
- `docker-compose.yml`: `EXTRA_GROUPS=dev,storage` — добавляет `boto3` и `pdfplumber` в образ.
- Тяжёлые группы (`parsing`, `llm`, `rag`, `pii`) подключаются по мере реализации спринтов.

## Тесты
27 unit-тестов (14 auth + 9 packages + 4 parsing), все проходят.

```
tests/unit/test_auth.py       14 passed
tests/unit/test_packages.py    9 passed  (upload, list, get, delete + edge cases)
tests/unit/test_parsing.py     4 passed  (pdfplumber, factory)
```

## Статусы пакета

```
RECEIVED → PROCESSING → PARSED
                      ↘ ERROR  (при исключении в pipeline)
```

После Sprint 3 добавится статус `DONE` (после успешного извлечения LLM).
