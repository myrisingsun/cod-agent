# Sprint 5 — PII фильтрация (Presidio)

## Что реализовано

### PresidioFilter (`app/pii/presidio_filter.py`)
Заменяет персональные данные типизированными плейсхолдерами перед отправкой текста в LLM.
После получения ответа от LLM — восстанавливает реальные значения.

**Распознаваемые сущности:**
| Тип | Описание |
|---|---|
| `PERSON` | ФИО (built-in Presidio) |
| `EMAIL_ADDRESS` | Email-адреса |
| `PHONE_NUMBER` | Номера телефонов |
| `IBAN_CODE` | IBAN банковских счетов |
| `CREDIT_CARD` | Номера карт |
| `DATE_TIME` | Даты |
| `LOCATION` | Адреса/местоположения |
| `RU_INN` | ИНН: 10 цифр (юр.л.) / 12 цифр (физ.л.) |
| `RU_CADASTRAL` | Кадастровый номер (NN:NN:NNNNNN:NNN) |
| `RU_PASSPORT` | Серия и номер паспорта (NNNN NNNNNN) |

**Механизм:**
```
filter("Иванов И.И., ИНН 770123456789")
→ "< PERSON_1>, ИНН <RU_INN_1>"
  mapping: {"<PERSON_1>": "Иванов И.И.", "<RU_INN_1>": "770123456789"}

restore("<PERSON_1> передаёт залог, ИНН <RU_INN_1>")
→ "Иванов И.И. передаёт залог, ИНН 770123456789"
```

**Особенности реализации:**
- Pattern-based режим: не требует загрузки spacy-модели (`en_core_web_sm` опционален, fallback при ошибке).
- Replacements применяются справа налево — индексы не смещаются.
- Несколько сущностей одного типа получают суффикс `_1`, `_2`, ...
- Экземпляр stateful: `_mapping` хранит соответствие для текущего документа.

### Активация в prod
```env
PII_FILTER=presidio
```
В dev остаётся `noop` — фильтр не применяется, накладных расходов нет.

### Зависимости Docker
`EXTRA_GROUPS="dev,storage,llm,rag,pii"` — добавляет `presidio-analyzer`, `presidio-anonymizer`, `spacy`.

> После установки spacy нужно: `python -m spacy download en_core_web_sm` (для NLP-режима).
> В pattern-only режиме spacy-модель не обязательна.

## Тесты
70 unit-тестов, все проходят.

```
tests/unit/test_auth.py         14 passed
tests/unit/test_packages.py      9 passed
tests/unit/test_parsing.py       4 passed
tests/unit/test_extraction.py   16 passed
tests/unit/test_rag.py          15 passed
tests/unit/test_pii.py          12 passed
  — NoopFilter (3): passthrough, restore, roundtrip
  — factory (2): noop default, presidio switch
  — PresidioFilter mocked (7): replace, mapping, restore, roundtrip,
                                multiple same type, no entities, empty mapping
```
