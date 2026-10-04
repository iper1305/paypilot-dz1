# PayPilot — ДЗ №1: вхід з L01 і Quality Bar Proposal

Документ, що здається: **[quality-bar-proposal.md](quality-bar-proposal.md)** — розділ 0 (вхід з L01) і розділи 1–7.

Усе побудовано на стенді PayPilot; даних і промптів інших компаній тут немає.

## На чому зроблено прогін

| Параметр | Значення |
|---|---|
| Скрипт | `l02_eval.py` (без змін), `cases.json` (13 кейсів), `requirements.txt` (`deepeval==4.2.6`) |
| Модель судді | **`claude-haiku-4-5`** — `JUDGE_MODEL` не задано, значення за замовчуванням скрипта; провайдер Anthropic |
| Агент (стенд) | `claude-haiku-4-5-20251001`, `LLM_PROVIDER=anthropic` |
| Профілі | **`clean`** × 4: 2 — baseline (`--profiles clean --baseline-runs 2`), 2 — у повному прогоні. **`lesson-02`** × 3 (D04, D05, D16, D19, D20, D25). |
| Годинник | `CLOCK_OVERRIDE=2026-09-15T10:00:00Z`; скрипт сам ставить його через `POST /api/_test/clock` |
| Дата прогону | 2026-10-04 |

## Як відтворити

Стенд PayPilot піднятий поруч, у `../paypilot-stand`, на `http://localhost:8000`, з `LLM_PROVIDER=anthropic`. У цьому каталозі створіть `.env` з `.env.example` і впишіть `ANTHROPIC_API_KEY` — той самий, що в `.env` стенду. Файл `.env` у репозиторій не потрапляє (`.gitignore`).

**Docker Compose ≥ 2.24:**

```bash
docker compose build
```

```bash
docker compose run --rm eval --profiles clean --baseline-runs 2
```

```bash
docker compose run --rm eval --runs 3 --baseline-runs 2
```

**Docker Compose 2.23.** Його `docker-compose.yml` не читає (`env_file … required: false`), тому прогін зроблено еквівалентом без compose — ті самі змінні й томи:

```bash
docker build -t l02-eval .
```

```bash
docker run --rm --env-file .env -e STAND_DIR=/stand -e SERVICE_URL=http://host.docker.internal:8000 --add-host host.docker.internal:host-gateway -v "$PWD":/work -v "$PWD/../paypilot-stand":/stand:ro l02-eval --profiles clean --baseline-runs 2
```

```bash
docker run --rm --env-file .env -e STAND_DIR=/stand -e SERVICE_URL=http://host.docker.internal:8000 --add-host host.docker.internal:host-gateway -v "$PWD":/work -v "$PWD/../paypilot-stand":/stand:ro l02-eval --runs 3 --baseline-runs 2
```

**Курований контекст** (розділ 1, hallucination rate). Додайте до будь-якої з команд вище такі прапорці:

```bash
--cases cases.curated.json --profiles clean,lesson-02 --runs 3 --baseline-runs 2 --metrics domain,faithfulness,hallucination
```

```bash
--cases cases.curated-c08.json --profiles clean,lesson-02 --runs 3 --baseline-runs 2 --metrics domain,hallucination
```

**Розділ 6 (перевірка правки).** Окремий контейнер стенду з виправленим §3. Промпт стенду й `prompts/base.v1.md` не змінюються.

1. Покладіть `lab-l02/section6-prompt-lesson02-fixed.md` як `base.v1.md` у теку `prompts/`, поруч створіть порожній `overlays/`.
2. Змонтуйте цю теку в образ стенду: `-v <тека>/prompts:/stand/prompts:ro`, порт 8001, змінні з `.env` стенду. Профіль `lesson-02` скрипт виставить сам.
3. Запустіть з обгорткою, що рахує токени судді:

```bash
docker run --rm --env-file .env -e STAND_DIR=/stand -e SERVICE_URL=http://host.docker.internal:8001 --add-host host.docker.internal:host-gateway -v "$PWD":/work -v "$PWD/../paypilot-stand":/stand:ro --entrypoint python l02-eval measure_judge_tokens.py reports/judge-tokens-s6-c01-c19.json --profiles lesson-02 --runs 3 --only C-01,C-19
```

## Звіти → числа в документі

| Файл | Що в ньому | Де використано |
|---|---|---|
| `reports/l02-clean-20261004-175135.json` (+ `step2-baseline-clean.txt`) | Baseline: clean ×2 | Точка відліку, шум clean |
| `reports/l02-clean-lesson-02-20261004-175622.json` (+ `step3-clean-lesson02.txt`) | Повний прогін: clean ×2 + lesson-02 ×3 | Дельти, пороги, trade-off (розд. 2–3), вартість (розд. 7) |
| `reports/l02-clean-lesson-02-20261004-180047.json` (+ `step5-curated.txt`) | Мій курований контекст: C-05, C-11, C-12 | Розд. 1–2, hallucination rate |
| `reports/l02-clean-lesson-02-20261004-180449.json` (+ `step5-c08-recurated.txt`) | C-08 з `fx-operations.md#s3` | Розд. 1, 4 — false positive через контекст |
| `reports/step4-compare.json` | clean vs lesson-02 для C-03 і C-05 + вивід рушія | Доказ false confidence |
| `reports/step1-c13-d16.json` | C-13 на clean і clean + D16 | Розд. 1, 4 — відкладений кейс пошуку |
| `reports/l02-lesson-02-20261004-181644.json`, `…-181817.json` (+ `section6-fix-*.txt`) | Правка з розділу 6 | Розд. 6 |
| `reports/judge-tokens-s6-*.json` | Токени кожного виклику судді (135 викликів) | Розд. 7 |

## Інші файли

| Файл | Що це |
|---|---|
| `specification-review.md`, `base.v1.1.md`, `prompts/CHANGELOG.md`, `prompt-governance-policy.md` | Матеріали L01; окремо не здаються |
| `l01-evidence/` | Сирі прогони L01: відповіді, трейси, програмні перевірки v1.1 |
| `lab-l02/` | Чернетка лабораторної L02: очікування до прогону (sha256 записано), гіпотеза розділу 6 (заморожена до правки), зібрані промпти lesson-02, скарги й дошка тріажу |
| `measure_judge_tokens.py` | Обгортка, що запускає `l02_eval.py` без змін і логує токени кожного виклику судді |

## Примітки

- **Звірка вартості з консоллю Anthropic** (розділ 7): Usage за 2026-10-04 (UTC) — 1,110,507 in / 170,720 out токенів Claude Haiku 4.5, тобто ≈ $1.96 за прайсом проти ≈ $1.94 за логами скрипта (≈ 1 %). Сторінка Cost на момент звірки (18:39 UTC) ще не показувала вартість за 4 жовтня.
- **Уточнення до L01.** У корпусі є `fx-operations.md#s3`, де правило безкоштовного ліміту сформульоване однозначно: спред на всю конвертацію, а не лише на частину понад ліміт. Отже, у `specification-review.md` (US-01, U7/U8) неоднозначні лише формулювання в `tariffs.md` і `fx-guide.md`, а рушій має опору в документах.
