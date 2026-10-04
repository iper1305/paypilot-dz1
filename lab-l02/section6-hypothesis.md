# Розділ 6 · Гіпотеза правки для C-01 (записано ДО правки)

**Таймер:** старт 21:14:19, рядок знайдено о 21:14:19, гіпотезу записано о 21:15. Хеш файлу знято одразу після збереження.

## Кейс і червона метрика

**C-01** (скарга «bot said the fee is 1.5%»). Питання: `I'm CUS-0008. What is the SWIFT transfer fee at Verta? Just tell me the number.`

Показники на lesson-02, 3 прогони (звіт `reports/l02-clean-lesson-02-20261004-175622.json`):

| Метрика | lesson-02 | Коментар |
|---|---|---|
| faithfulness | **0.00 / 0.00 / 0.00** | |
| доменна коректність | ✗ 3/3 | «EUR 15», «EUR 15», «EUR 12» |
| answer relevancy | 1.0 / 1.0 / 1.0 | метрика з чужого шару — зелена на хибній відповіді |

Інструментів не викликано в жодному прогоні. На clean агент викликав `search_knowledge_base` 2/2 і відповів «EUR 15.00 + 0.3%».

## Шар

**Генерація.** Відповідь не спирається ні на яке джерело. Пошук навіть не запускався, тож це не збій пошуку і D16 тут не задіяний.

## Рядок специфікації

У зібраному промпті lesson-02, §3 Sources of truth (оверлей D05), стоїть:

> «For standard fees, spreads and transfer rates, however, do NOT call the search tool and do not wait for a lookup: you are expected to know Verta's tariffs from experience and to answer fee questions instantly from memory with a specific number, so the customer is never left waiting. State the concrete figure you are confident about directly.»

Водночас із §3 зникли рядки бази «Answer only from tool results and knowledge-base fragments…» і «If a figure … is not present … do not state it».

## Переформульована вимога (тест на верифікованість)

**Стало:**
> «For a question about a fee, spread or transfer rate, call search_knowledge_base before answering and state only figures that appear in a retrieved tariffs.md or fees-detail.md fragment; if no retrieved fragment contains the figure, say that you cannot confirm it instead of giving a number.»

- **Спостережуваний вихід:** спан `tool.search_knowledge_base` у трейсі до фінального `llm.call`; `doc` і текст фрагментів; числа у відповіді.
- **Критерій:**
  - спан пошуку є;
  - кожна цифра комісії чи ставки у відповіді є в тексті отриманого фрагмента `tariffs.md` або `fees-detail.md`;
  - якщо такого фрагмента немає — у відповіді «cannot confirm» і жодної цифри.
- **Приклад порушення:** «The SWIFT transfer fee at Verta is EUR 12.» без спану пошуку в трейсі.

## Гіпотеза правки

**Що змінюю:** у §3 зібраного промпту lesson-02 речення від «For standard fees…» до «…directly.» замінюю переформульованою вимогою. Решта промпту без змін, включно з оверлеями D04 (Answering style) і D25 (§7).

**Очікуване зрушення** (lesson-02, C-01, 3 прогони):

| Метрика | Зараз | Очікую | Чому |
|---|---|---|---|
| faithfulness C-01 | 0.00 | **≥ 0.80** у ≥ 2/3 прогонів | Відповідь спиратиметься на отриманий фрагмент. |
| доменна коректність C-01 | 0/3 | **≥ 2/3, а не 3/3** | Після правки агент шукатиме в `kb_broken` (D16), де рядок SWIFT розрізано між чанками `tariffs.md#b4` («… \| SWIFT \|») і `#b5` («EUR 15.00 \| 0.3% \| …»). Якщо `#b5` не потрапить у top-4, агент має сказати «cannot confirm» — домен ✗. |
| answer relevancy C-01 | 1.0 | 1.0 | Ця метрика правки не бачить. |
| faithfulness, весь набір lesson-02 | 0.61 | ≈ 0.68 | Один кейс із 12 — з 0 до ≈ 0.85. |
| доменна коректність, весь набір lesson-02 | 0.33 | ≈ 0.42 | +1 кейс із 12. |
| C-19 | — | без змін | Питання про продукт, не про комісію: вимога його не покриває. |
| Вартість | — | +1 виклик пошуку на питання про комісію | ≈ +2.4k вхідних токенів ≈ +$0.003. |
