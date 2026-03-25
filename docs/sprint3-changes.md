# Sprint 3 — LLM + извлечение полей

## Что реализовано

### LLM клиент (`app/llm/openai_compat.py`)
- `OpenAICompatClient` — async-клиент на базе `openai` SDK.
  Совместим с Ollama (`http://ollama:11434/v1`), vLLM и OpenAI API.
  Поддержка JSON-mode через `response_format: {type: json_object}`.

### Prompts (`app/prompts/extraction.py`)
- Системный промпт на русском с чёткой инструкцией по извлечению 10 полей.
- Формат ответа: `{"field": {"value": "...", "confidence": 0.0–1.0}}`.
- 1 few-shot пример (реальный залоговый договор) для повышения точности.
- `build_user_prompt()` — включает few-shot или RAG-чанки (Sprint 4).

### Extraction модуль (`app/extraction/llm_extractor.py`)
- `LLMExtractor.extract()` — вызывает LLM, парсит JSON, валидирует через Pydantic.
- `_parse_llm_json()` — устойчив к markdown-обёрткам и мусору в ответе LLM.
- `_build_result()` — нормализует `area_sqm` (str→float), зажимает confidence в [0, 1].
- Flat-value fallback: если LLM вернул `"field": "value"` вместо `{value, confidence}`.
- Документ обрезается до 12 000 символов (~3k токенов) перед отправкой в LLM.

### RAG заглушка (`app/rag/null_retriever.py`)
- `NullRetriever` — возвращает пустой список. Используется до Sprint 4.
- `rag/factory.py` обновлён: при `ImportError` (нет `sentence-transformers`) fallback на NullRetriever.

### Pipeline (`app/pipeline/process_package.py`)
Полный pipeline RECEIVED → DONE:
1. `Storage.get()` — байты из MinIO
2. `Parser.parse()` → `ParsedDocument`
3. `PIIFilter.filter()` — очистка (noop в dev)
4. `LLMExtractor.extract()` → `PledgeFields` + `FieldConfidence`
5. Сохранение `ExtractionResult` в PostgreSQL (JSONB)
6. Обновление `Package.accuracy` (среднее confidence ненулевых полей) + `status=done`

### Extraction API (`app/api/routes_extraction.py`)
| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/packages/{id}/extraction` | Результат извлечения + confidence по каждому полю |
| `POST` | `/packages/{id}/extraction/retry` | Повторный запуск pipeline (status=error/done → received) |

Retry возвращает 409, если пакет уже в статусе `processing`.

### Статусная модель (обновление)
```
RECEIVED → PROCESSING → DONE
                      ↘ ERROR
```
Статус `parsed` добавлен в `PackageStatus` enum (схема), но pipeline идёт сразу до `done`.

## Тесты
43 unit-теста, все проходят.

```
tests/unit/test_auth.py         14 passed
tests/unit/test_packages.py      9 passed
tests/unit/test_parsing.py       4 passed
tests/unit/test_extraction.py   16 passed
  — JSON parsing (4): clean, markdown fence, garbage, inner JSON
  — _build_result (5): full response, nulls, area_sqm coercion, clamp, flat fallback
  — LLMExtractor (2): happy path, bad LLM response
  — API endpoints (5): get success, 404 package, 404 no result, retry 202, retry 409
```

## Настройки

| Переменная | Dev | Prod |
|---|---|---|
| `LLM_BASE_URL` | `http://ollama:11434/v1` | vLLM endpoint |
| `LLM_MODEL` | `qwen2.5:7b` | любая совместимая модель |
| `LLM_TIMEOUT` | `120` | настраивается |
