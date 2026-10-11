# L03 · Самостійна робота — золотий набір PayPilot

Звіт: **[self-study-l03-iryna.md](self-study-l03-iryna.md)** — розкладка скарг, кейс руками, генератор, драбина перевірок, три прогони і дельта між ними.

| Прогін (набір v2, `set_hash 69f072184cdc`) | Результат |
|---|---|
| baseline `clean` | 39/40 |
| `lesson-03` | 23/40 |
| `clean` + «Round all amounts to whole numbers for readability.» | 30/40 |
| контроль після відновлення промпту | 2/2 |

## Що тут

| Файл | Що це |
|---|---|
| `sets/l03-iryna.jsonl` | Набір v2, 40 кейсів; з ним зроблено фінальні прогони |
| `sets/l03-iryna-v1.jsonl` | Набір v1 (`d4d00f329a08`); що в ньому змінилось і чому — у звіті, розділ 5 |
| `generate_mine.py` | Генератор: рушії стенду + `app/seed.py` як список операцій; дописує ручні кейси |
| `cases-manual-iryna.jsonl` | 11 ручних кейсів: скарги + 6 кейсів з оракулом human |
| `case-CMP-12.json` | Кейс, записаний повністю руками |
| `reports/` | JSON-звіти ранера, повний вивід кожного прогону (`*.log`) і `v2-delta.json` |
| `runner.py`, `cli.py`, `loader.py`, `assertions.py`, `stand.py`, `judge.py`, `console.py`, `validate.py`, `docker-compose.yml`, `.env.example`, `complaints.md`, `triage.md` | Ранер і матеріали курсу з [paypilot-l03-eval](https://github.com/sergeytkachenko/paypilot-l03-eval), коміт `b9ee5fb` |

Ранер курсу взято без змін, крім одного рядка: у `judge.py` `max_tokens` 400 → 2048. Суддя `claude-haiku-5-5` за замовчуванням думає, і на 400 токенах JSON вердикту обривався, а ранер падав без звіту.

## Як відтворити

1. Стенд PayPilot піднятий на `http://localhost:8000` з живою моделлю.
2. Цей репозиторій лежить поруч зі стендом, тобто стенд — у `../../paypilot-stand` відносно цієї теки.
3. Тут створено `.env` з `.env.example`: `JUDGE_MODEL=claude-haiku-5-5` і `ANTHROPIC_API_KEY` — ключ судді рівня 7. У репозиторій `.env` не потрапляє.

Зібрати набір:

```bash
docker run --rm -v "$PWD":/course/solutions/evals -v "$PWD/../../paypilot-stand/app":/course/app:ro -w /course/solutions/evals --entrypoint python python:3.12-slim generate_mine.py > sets/l03-iryna.jsonl
```

Прогнати (`--profile clean`, потім `--profile lesson-03`):

```bash
docker run --rm --env-file .env -e SET=l03-iryna -e GATE= -e SERVICE_URL=http://host.docker.internal:8000 --add-host host.docker.internal:host-gateway -v "$PWD":/course/solutions/evals -v "$PWD/../../paypilot-stand/app":/course/app:ro -w /course/solutions/evals --entrypoint python python:3.12-slim cli.py --profile clean --gate all
```

З Docker Compose ≥ 2.24 те саме — `docker compose run --rm eval --set l03-iryna --profile clean --gate all`, з `STAND_DIR=../../paypilot-stand` у `.env`. Compose 2.23 файл курсу не читає (`env_file … required: false`), тому тут команди без compose.

`--gate all` потрібен, бо HUM-17, HUM-02 і HUM-18 позначено `gate: release`.

Клієнта кейса я пишу і в тексті («I'm CUS-…»), і в `context.customer_id`. Тоді кейси працюють і на стенді, що бере клієнта з тексту, і на стенді з ADR 0001.
