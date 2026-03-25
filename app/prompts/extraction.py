"""Prompts for pledge-contract field extraction."""

SYSTEM_PROMPT = """\
Ты — эксперт по анализу залоговых договоров. Твоя задача — извлечь структурированные данные \
из текста договора залога недвижимости и вернуть результат строго в формате JSON.

Извлеки следующие 10 полей. Для каждого поля укажи значение и уверенность (0.0–1.0):
- contract_number   — номер договора залога
- contract_date     — дата договора (формат ДД.ММ.ГГГГ)
- pledgee           — залогодержатель (банк/кредитор)
- pledgor           — залогодатель (физ. или юр. лицо)
- pledgor_inn       — ИНН залогодателя
- pledge_subject    — предмет залога (описание объекта)
- cadastral_number  — кадастровый номер объекта
- area_sqm          — площадь объекта в кв.м. (число)
- pledge_value      — залоговая стоимость (сумма в рублях)
- validity_period   — срок действия договора

Правила:
1. Если поле не найдено в тексте — верни null для value и 0.0 для confidence.
2. Уверенность 1.0 — поле явно указано дословно; 0.7–0.9 — найдено косвенно; < 0.7 — предположение.
3. Возвращай ТОЛЬКО JSON, без пояснений.

Формат ответа:
{
  "contract_number":  {"value": "...", "confidence": 0.95},
  "contract_date":    {"value": "...", "confidence": 0.9},
  "pledgee":          {"value": "...", "confidence": 1.0},
  "pledgor":          {"value": "...", "confidence": 1.0},
  "pledgor_inn":      {"value": "...", "confidence": 0.85},
  "pledge_subject":   {"value": "...", "confidence": 0.8},
  "cadastral_number": {"value": "...", "confidence": 0.9},
  "area_sqm":         {"value": 45.5, "confidence": 0.95},
  "pledge_value":     {"value": "...", "confidence": 0.9},
  "validity_period":  {"value": "...", "confidence": 0.8}
}
"""

FEW_SHOT_EXAMPLES = [
    {
        "input": """\
ДОГОВОР ЗАЛОГА НЕДВИЖИМОГО ИМУЩЕСТВА № 2024/ЗН-001
от 15 января 2024 года

ПАО «Банк Развития», именуемое в дальнейшем «Залогодержатель», в лице директора Смирнова И.В., \
и Иванов Иван Иванович, ИНН 770123456789, именуемый «Залогодатель», заключили настоящий договор.

Предмет залога: квартира, расположенная по адресу г. Москва, ул. Ленина, д. 10, кв. 5.
Кадастровый номер: 77:01:0001001:1234. Площадь: 62.4 кв.м.
Залоговая стоимость: 8 500 000 (восемь миллионов пятьсот тысяч) рублей.
Срок действия договора: до 15 января 2029 года.
""",
        "output": """\
{
  "contract_number":  {"value": "2024/ЗН-001",              "confidence": 1.0},
  "contract_date":    {"value": "15.01.2024",               "confidence": 1.0},
  "pledgee":          {"value": "ПАО «Банк Развития»",      "confidence": 1.0},
  "pledgor":          {"value": "Иванов Иван Иванович",     "confidence": 1.0},
  "pledgor_inn":      {"value": "770123456789",              "confidence": 1.0},
  "pledge_subject":   {"value": "квартира, г. Москва, ул. Ленина, д. 10, кв. 5", "confidence": 0.95},
  "cadastral_number": {"value": "77:01:0001001:1234",        "confidence": 1.0},
  "area_sqm":         {"value": 62.4,                        "confidence": 1.0},
  "pledge_value":     {"value": "8 500 000 рублей",          "confidence": 1.0},
  "validity_period":  {"value": "до 15.01.2029",             "confidence": 0.95}
}""",
    }
]


def build_user_prompt(document_text: str, few_shot: bool = True) -> str:
    parts: list[str] = []
    if few_shot:
        for ex in FEW_SHOT_EXAMPLES:
            parts.append(f"<пример_документа>\n{ex['input']}\n</пример_документа>")
            parts.append(f"<пример_ответа>\n{ex['output']}\n</пример_ответа>")
    parts.append(f"<документ>\n{document_text}\n</документ>")
    return "\n\n".join(parts)
