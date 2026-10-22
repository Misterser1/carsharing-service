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
| 3+ | Реализация API, БД, аутентификации и т. д. | ⏳ | — |

## Структура репозитория

```
.
├── README.md                 # описание репозитория (этот файл)
├── ARCHITECTURE.md           # архитектурный отчёт: роли, use cases, C4, ERD, 3NF, контрольные вопросы
├── openapi.yaml              # контракт REST API по OpenAPI 3.0 (ЛР2)
├── db/
│   └── schema.sql            # DDL PostgreSQL 16: таблицы, ENUM, PK/FK, CHECK, UNIQUE, индексы
└── docs/
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
