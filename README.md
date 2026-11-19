# Carsharing / Rental API — сервис аренды автомобилей

Сквозной проект по дисциплине **«Разработка серверных приложений»**.
Вариант 5 — *Сервис аренды автомобилей (Carsharing / Rental API)*.

> **Студент:** ___________________  **Группа:** ___________

Серверное приложение для краткосрочной аренды автомобилей: водитель находит свободное авто на карте, бронирует его с блокировкой депозита, начинает и завершает поездку; система учитывает пробег и уровень топлива, рассчитывает стоимость и списывает оплату. Оператор автопарка управляет автомобилями, тарифами, верифицирует водителей и разбирает инциденты.

## Статус работ

| № | Лабораторная работа | Статус | Результат |
|---|---|---|---|
| 1 | Проектирование архитектуры серверного приложения и предметной области | ✅ выполнена | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 2 | Проектирование REST API и спецификация OpenAPI 3.0 | ✅ выполнена | [openapi.yaml](openapi.yaml), раздел [REST API Specs](ARCHITECTURE.md#4-rest-api-specs-openapi) |
| 3 | Базовый каркас приложения, Clean / Layered Architecture, настройка окружения | ✅ выполнена | [Отчёт и ответы на вопросы](docs/lab3.md), [app/](app/), [tests/](tests/), [.env.example](.env.example) |
| 4 | Контейнеризация приложения с Docker, оптимальный Dockerfile | ✅ выполнена | [Отчёт и ответы на вопросы](docs/lab4.md), [Dockerfile](Dockerfile), [.dockerignore](.dockerignore) |
| 5+ | PostgreSQL и миграции, репозитории, аутентификация и т. д. | ⏳ | — |

## Структура репозитория

```
.
├── README.md                 # описание репозитория (этот файл)
├── ARCHITECTURE.md           # архитектурный отчёт: роли, use cases, C4, ERD, 3NF, контрольные вопросы
├── openapi.yaml              # контракт REST API по OpenAPI 3.0 (ЛР2)
├── Dockerfile                # образ приложения: python:3.12-slim, многоэтапная сборка (ЛР4)
├── .dockerignore             # что не попадает в контекст сборки образа (ЛР4)
├── app/                      # серверное приложение (ЛР3)
│   ├── main.py               # сборка FastAPI: настройки, middleware, обработчики ошибок, роутеры
│   ├── __main__.py           # запуск через `python -m app`
│   ├── api/                  # HTTP-слой: роутеры, зависимости (DI), формат ошибок, request_id
│   │   └── v1/               # эндпоинты /api/v1/...
│   ├── services/             # бизнес-логика (правила предметной области)
│   ├── repositories/         # доступ к данным: интерфейс + реализация в памяти
│   ├── models/               # доменные сущности
│   ├── schemas/              # Pydantic-схемы запросов и ответов
│   └── core/                 # конфигурация (env), логирование, доменные исключения
├── tests/                    # pytest: конфигурация, сервис, API
├── requirements.txt          # зависимости приложения
├── requirements-dev.txt      # + зависимости для тестов и линтера
├── pyproject.toml            # настройки pytest и ruff
├── .env.example              # пример переменных окружения (копируется в .env)
├── db/
│   └── schema.sql            # DDL PostgreSQL 16: таблицы, ENUM, PK/FK, CHECK, UNIQUE, индексы
└── docs/
    ├── lab3.md               # отчёт ЛР3: структура, окружение, демонстрация, контрольные вопросы
    ├── lab4.md               # отчёт ЛР4: Dockerfile, сборка и запуск контейнера, контрольные вопросы
    └── diagrams/
        ├── c4-context.puml   # C4 Level 1 — System Context (PlantUML + C4-PlantUML)
        ├── c4-container.puml # C4 Level 2 — Container
        ├── use-cases.puml    # диаграмма вариантов использования
        ├── erd.mmd           # ER-диаграмма (Mermaid)
        ├── erd.dbml          # ER-диаграмма для dbdiagram.io
        ├── rental-flow.mmd   # sequence: жизненный цикл аренды с депозитом
        ├── vehicle-states.mmd, rental-states.mmd   # диаграммы состояний
        ├── *.png, *.svg      # экспортированные изображения
        └── render.sh / render.ps1                  # перегенерация изображений через kroki.io
```

## Запуск приложения

Нужен Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                 # Windows: copy .env.example .env
python -m app
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs (ReDoc — `/redoc`)
- Проверка: `curl http://localhost:8000/api/v1/health`

Запуск в Docker (нужен Docker Engine 24+):

```bash
docker build -t carsharing-api:latest .
docker run --name backend-container -d -p 8080:8080 -e HTTP_PORT=8080 carsharing-api:latest
curl http://localhost:8080/api/v1/health
docker logs backend-container
docker stop backend-container && docker rm backend-container
```

В образе по умолчанию `APP_ENV=production` (Swagger UI выключен) и `HTTP_PORT=8080`; любые настройки из таблицы ниже передаются через `-e`, например `-e APP_ENV=development`.

Тесты и линтер:

```bash
pytest
ruff check .
```

Сейчас реализованы `GET /api/v1/health` (и `/health` без префикса) и управление автопарком `/api/v1/vehicles` (список с фильтрами и пагинацией, создание, получение, изменение, списание) — сквозной пример, проходящий через все слои. Данные хранятся в памяти и пропадают при перезапуске; PostgreSQL подключается в ЛР5–6, аутентификация по JWT — в следующих работах.

### Слои и правило зависимостей

```
HTTP-запрос
   │
   ▼
api/         роутеры: разбор запроса, валидация схем, коды ответа        ← знает про HTTP
   │  вызывает
   ▼
services/    бизнес-правила: уникальность госномера и VIN,                ← не знает про HTTP и БД
   │         допустимые переходы статусов, запрет списания авто в аренде
   │  через интерфейс VehicleRepository
   ▼
repositories/ хранение: сейчас InMemoryVehicleRepository, потом PostgreSQL ← знает про хранилище
```

- Зависимости направлены только вниз: `api → services → repositories`. Сервис получает репозиторий через конструктор (`VehicleService(repository)`), а не создаёт его сам, поэтому хранилище меняется без правок бизнес-логики.
- Сервис бросает доменные исключения (`NotFoundError`, `ConflictError` из `app/core/exceptions.py`), а API-слой переводит их в HTTP-коды 404 / 409 и единый ответ `ErrorResponse` из спецификации.
- Связывание слоёв — в `app/api/deps.py` через `Depends` FastAPI; в тестах сервис проверяется отдельно, без HTTP.

### Переменные окружения

Настройки читаются модулем `app/core/config.py` из переменных окружения и из файла `.env` (переменные окружения важнее). Файл `.env` в git не попадает, в репозитории лежит шаблон [.env.example](.env.example).

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `APP_NAME` | `Carsharing Rental API` | Название сервиса в `/api/v1/health` |
| `APP_ENV` | `development` | Окружение: `development`, `test`, `production`. В `production` отключены `/docs`, `/redoc`, `/openapi.json` |
| `APP_VERSION` | `1.0.0` | Версия в `/api/v1/health` и в OpenAPI |
| `APP_DEBUG` | `false` | Режим отладки FastAPI |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `HTTP_HOST` | `0.0.0.0` | Адрес HTTP-сервера |
| `HTTP_PORT` | `8000` | Порт HTTP-сервера (в Docker-образе — `8080`) |
| `HTTP_RELOAD` | `false` | Автоперезагрузка при изменении кода (в `.env.example` включена для локальной разработки, в Docker выключена) |
| `CORS_ORIGINS` | — | Разрешённые источники для CORS через запятую |

## Ключевые архитектурные решения

- **Стек:** Python 3.12 + FastAPI (Backend API), Celery (фоновый воркер), PostgreSQL 16, Redis 7, RabbitMQ, S3/MinIO. Клиенты — React Native (водитель) и React SPA (оператор).
- **Стиль:** модульный монолит — один API-процесс со слоями `api → services → repositories` и отдельный воркер для платежей, уведомлений и телематики.
- **Данные:** 15 таблиц в 3НФ; статусы авто / аренды / депозита — конечные автоматы; защита от двойного бронирования — TTL-лок в Redis + частичный уникальный индекс в PostgreSQL.
- **Депозит:** двухстадийные платежи (hold → release / capture) через платёжный шлюз, отдельная сущность `deposit_holds`.

Подробности — в [ARCHITECTURE.md](ARCHITECTURE.md).

## Как посмотреть диаграммы

- Готовые изображения лежат в [docs/diagrams/](docs/diagrams/) и вставлены в `ARCHITECTURE.md`.
- Mermaid-диаграммы (`*.mmd`) GitHub рендерит прямо в Markdown; их также можно открыть на [mermaid.live](https://mermaid.live).
- PlantUML (`*.puml`) — на [plantuml.com/plantuml](https://www.plantuml.com/plantuml/uml/) или в IDE-плагине PlantUML.
- DBML (`erd.dbml`) — импорт в [dbdiagram.io](https://dbdiagram.io) (Import → From DBML).

Перегенерировать PNG/SVG после правки исходников (нужен доступ в интернет, используется публичный сервис [kroki.io](https://kroki.io)):

```bash
bash docs/diagrams/render.sh                                     # Linux / macOS / Git Bash
powershell -ExecutionPolicy Bypass -File docs\diagrams\render.ps1  # Windows PowerShell
```

## Как применить схему БД

```bash
createdb carsharing
psql -d carsharing -f db/schema.sql
```

Схема создаёт расширение `pgcrypto` (для `gen_random_uuid()`), 13 ENUM-типов, 15 таблиц с ограничениями и 29 индексов, а также заполняет справочники классов автомобилей и опций.
