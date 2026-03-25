# Sprint 4 — RAG (векторный поиск + Q&A чат)

## Что реализовано

### Chunker (`app/pipeline/chunker.py`)
- `chunk_text(text, chunk_size=400, overlap_ratio=0.15)` — разбивка текста на чанки по словам.
- Overlap гарантирует сохранность контекста на границах чанков.
- Нет внешних зависимостей — работает в любом окружении.

### Qdrant Retriever (`app/rag/qdrant_retriever.py`)
- `QdrantRetriever`: BGE-M3 (`BAAI/bge-m3`) через `sentence-transformers`, индекс в Qdrant.
- `index(chunks, collection, metadata)` — загрузка чанков с авто-созданием коллекции.
- `retrieve(query, collection, top_k=5)` — dense cosine-поиск, возвращает `RetrievedChunk`.
- Модель загружается один раз через `@lru_cache` — не перезагружается между запросами.
- Обе операции неблокирующие: `run_in_executor` для CPU-intensive embedding.

### BaseRetriever обновлён
- Добавлен метод `index()` в Protocol и `NullRetriever`.

### ChatMessage модель + миграция
- `app/models/chat_message.py` — таблица `chat_messages`:
  `id`, `package_id` (FK→packages CASCADE), `role`, `content`, `sources` (JSONB), `created_at`.
- `alembic/versions/002_chat_messages.py` — миграция применена.

### Pipeline шаг 4: RAG индексирование (`app/pipeline/process_package.py`)
После парсинга и PII-фильтрации:
- `chunk_text(clean_text)` → список чанков
- `retriever.index(chunks, "current_packages", metadata=[{package_id, filename}])`
- Экстрактор теперь получает retriever и может использовать `reference_templates` для few-shot.

### Chat API (`app/api/routes_chat.py`)
| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/packages/{id}/chat` | Вопрос по документу: RAG retrieve → LLM → ответ с источниками |
| `GET` | `/packages/{id}/chat/history` | История сообщений (user + assistant) |

- `POST /chat`: доступен только при `status=done|parsed`, иначе 409.
- Чанки фильтруются по `package_id` из metadata — пользователь видит только свои данные.
- Сохраняются оба сообщения (user + assistant) с `sources` в JSONB.

### Коллекции Qdrant
| Коллекция | Назначение |
|---|---|
| `current_packages` | Чанки загруженных документов (Q&A) |
| `reference_templates` | Эталонные договоры для few-shot (Sprint 5 / ручная загрузка) |

## Тесты
58 unit-тестов, все проходят.

```
tests/unit/test_auth.py         14 passed
tests/unit/test_packages.py      9 passed
tests/unit/test_parsing.py       4 passed
tests/unit/test_extraction.py   16 passed
tests/unit/test_rag.py          15 passed
  — chunker (6): empty, single, multiple, size, overlap, coverage
  — NullRetriever (2): index noop, retrieve empty
  — chat ask (4): success, not ready 409, not found 404, no token 401
  — chat history (3): messages, empty, not found 404
```

## Зависимости Docker
`EXTRA_GROUPS="dev,storage,llm,rag"` — добавляет `qdrant-client`, `sentence-transformers`, `langchain`.

> Первый запуск с RAG: модель BGE-M3 (~570 МБ) скачивается при первом обращении к retriever.
