# ЛР4. Контейнеризация серверного приложения с Docker, оптимальный Dockerfile

Вариант 5 — Carsharing / Rental API. Стек: Python 3.12, FastAPI. Docker Engine 29.1.3, BuildKit (buildx 0.30.1).

## 1. Что сделано

| Задание | Результат |
|---|---|
| 1. `.dockerignore` | [`.dockerignore`](../.dockerignore): Git, `.env`, `.venv`, кэши, тесты, логи, документация. В контекст сборки попадают только `app/` и `requirements.txt` (25 файлов, 28 КБ) |
| 2. Оптимизированный `Dockerfile` | [`Dockerfile`](../Dockerfile): многоэтапная сборка на минимальном образе `python:3.12-slim` |
| 3. Сборка образа | `docker build -t carsharing-api:latest .` — без предупреждений |
| 4. Запуск с `-p` и `-e` | `docker run --name backend-container -d -p 8080:8080 -e HTTP_PORT=8080 carsharing-api:latest` |
| 5. Проверка `/health` | `curl http://localhost:8080/api/v1/health` → `200 OK`; контейнер в состоянии `healthy` |

## 2. Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

# --- Этап сборки (Builder): зависимости ставятся в отдельное виртуальное окружение ---
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Сначала только список зависимостей: этот слой берётся из кэша,
# пока requirements.txt не меняется, даже если поменялся код
COPY requirements.txt .
RUN pip install -r requirements.txt

# --- Финальный лёгкий этап: только Python, готовые зависимости и код ---
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production \
    HTTP_HOST=0.0.0.0 \
    HTTP_PORT=8080

# Приложение работает не от root
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Копируем установленные зависимости из этапа сборки, без pip-кэша и инструментов
COPY --from=builder /opt/venv /opt/venv
COPY app ./app

USER appuser

# Открываем порт приложения
EXPOSE 8080

# Docker сам проверяет здоровье контейнера через health-эндпоинт
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('HTTP_PORT', '8080') + '/api/v1/health', timeout=2)" || exit 1

# Команда запуска: хост и порт берутся из HTTP_HOST / HTTP_PORT
CMD ["python", "-m", "app"]
```

Что сделано для оптимизации:

- **Минимальный базовый образ** `python:3.12-slim`, как рекомендует задание для интерпретируемых языков, той же версии Python, что и в разработке.
- **Многоэтапная сборка.** На этапе `builder` зависимости ставятся в виртуальное окружение `/opt/venv`; в финальный образ копируется только это окружение и папка `app/` — без pip-кэша, `requirements.txt` и промежуточных файлов.
- **Порядок слоёв для кэша.** `requirements.txt` копируется и устанавливается раньше кода (см. ответ на вопрос 4).
- **Безопасность.** Приложение работает от непривилегированного пользователя `appuser` (uid 10001), а не от root; секретов в образе нет — `.env` исключён, настройки передаются через `-e`.
- **Настройки через переменные окружения.** В образе заданы значения по умолчанию (`APP_ENV=production`, `HTTP_PORT=8080`), при запуске их меняют через `-e`. В `production` Swagger UI отключён, автоперезагрузка кода (`HTTP_RELOAD`) выключена.
- **`HEALTHCHECK`.** Docker сам раз в 30 секунд опрашивает `/api/v1/health` и показывает состояние контейнера (`healthy` / `unhealthy`). В образе нет `curl`, поэтому проверка написана на Python.
- **Корректная остановка.** `CMD` в exec-форме: приложение — процесс с PID 1 и само получает сигнал `SIGTERM` от `docker stop`.

## 3. Демонстрация

### Сборка образа

```
$ docker build -t carsharing-api:latest .
#7 [builder 1/5] FROM docker.io/library/python:3.12-slim
#8 [builder 2/5] RUN python -m venv /opt/venv
#9 [stage-1 2/5] RUN useradd --create-home --uid 10001 appuser
#10 [stage-1 3/5] WORKDIR /app
#11 [builder 3/5] WORKDIR /build
#12 [builder 4/5] COPY requirements.txt .
#13 [builder 5/5] RUN pip install -r requirements.txt
#13 6.891 Successfully installed annotated-types-0.8.0 anyio-4.16.0 click-8.5.1 fastapi-0.115.12 h11-0.16.0 httptools-0.9.0 idna-3.20 pydantic-2.11.4 pydantic-core-2.33.2 pydantic-settings-2.9.1 python-dotenv-1.2.4 pyyaml-6.0.3 starlette-0.46.2 typing-extensions-4.16.0 typing-inspection-0.4.5 uvicorn-0.34.2 uvloop-0.23.0 watchfiles-1.3.0 websockets-17.4
#14 [stage-1 4/5] COPY --from=builder /opt/venv /opt/venv
#15 [stage-1 5/5] COPY app ./app
#16 naming to docker.io/library/carsharing-api:latest done
#16 DONE 5.5s
```

Выведены шаги сборки (полный журнал — `docker build --progress=plain`). Сборка завершилась успешно, в полном журнале нет ни одного предупреждения (`WARN`).

```
$ docker images carsharing-api
IMAGE                   ID             DISK USAGE   CONTENT SIZE   EXTRA
carsharing-api:latest   283adfced535        250MB         59.4MB
```

`CONTENT SIZE` — сжатый размер слоёв, который скачивается из реестра; `DISK USAGE` — место на диске в распакованном виде.

Внутри образа только нужное: приложение работает от `appuser`, в `/app` лежит только `app/`, тестов, `.env` и `__pycache__` нет:

```
$ docker run --rm --entrypoint sh carsharing-api:latest -c 'id; ls -A /app'
uid=10001(appuser) gid=10001(appuser) groups=10001(appuser)
app
```

### Запуск контейнера и проверка

```
$ docker run --name backend-container -d -p 8080:8080 -e HTTP_PORT=8080 carsharing-api:latest
14879305d6e2e5d586befd3160c1b9c339c4463ff172e528900e947b09f447ca

$ curl -i http://localhost:8080/api/v1/health
HTTP/1.1 200 OK
date: Thu, 19 Nov 2026 09:17:25 GMT
server: uvicorn
content-length: 116
content-type: application/json
x-request-id: 56986aa8-5949-4a3e-8f34-2156fdc825ad

{"status":"pass","app_name":"Carsharing Rental API","version":"1.0.0","environment":"production","uptime_seconds":0}

$ docker ps
CONTAINER ID   IMAGE                   COMMAND           CREATED          STATUS                    PORTS                                         NAMES
14879305d6e2   carsharing-api:latest   "python -m app"   41 seconds ago   Up 37 seconds (healthy)   0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp   backend-container

$ docker logs backend-container
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     172.17.0.1:43288 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     172.17.0.1:43294 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:49244 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58524 - "GET /api/v1/health HTTP/1.1" 200 OK
```

Контейнер в состоянии `healthy`: встроенный `HEALTHCHECK` опрашивает эндпоинт изнутри контейнера (запросы с `127.0.0.1` в журнале), запросы с `172.17.0.1` — это `curl` с хост-машины через проброшенный порт. Тот же ответ доступен в браузере или Postman по адресу http://localhost:8080/api/v1/health.

Переменные окружения из `-e` меняют поведение без пересборки образа:

```
$ docker run --name env-demo -d -p 9090:9090 -e HTTP_PORT=9090 -e APP_ENV=development -e APP_NAME="Carsharing Demo" carsharing-api:latest
$ curl http://localhost:9090/api/v1/health
{"status":"pass","app_name":"Carsharing Demo","version":"1.0.0","environment":"development","uptime_seconds":0}
```

### Остановка и удаление

```
$ docker stop backend-container
backend-container
# заняло 2.5 с

$ docker logs --tail 4 backend-container
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]

$ docker rm backend-container
backend-container
```

Приложение — процесс с PID 1 — получает `SIGTERM` от `docker stop` и завершается само, не дожидаясь принудительного `SIGKILL` через 10 секунд.

## 4. Ответы на контрольные вопросы

### 4.1 В чём главное отличие виртуальной машины от Docker-контейнера?

Виртуальная машина эмулирует целый компьютер: гипервизор выделяет ей виртуальное железо, и внутри работает **полноценная гостевая ОС со своим ядром**. Контейнер своего ядра не имеет: это обычный процесс **хостовой ОС**, который ядро изолирует с помощью namespaces (своя файловая система, сеть, процессы) и ограничивает cgroups (CPU, память).

Отсюда практическая разница:

| | Виртуальная машина | Контейнер |
|---|---|---|
| Ядро ОС | своё, гостевое | общее с хостом |
| Размер | гигабайты (целая ОС) | десятки–сотни мегабайт (только приложение и библиотеки) |
| Запуск | минуты: загрузка ОС | секунды: старт процесса |
| Изоляция | сильнее: граница — гипервизор | слабее: общее ядро |
| Можно запустить другую ОС | да (Windows на Linux) | только программы под ядро хоста |

Контейнер легче и быстрее, поэтому на одном сервере их помещается намного больше, чем виртуальных машин; ВМ выбирают, когда нужна другая ОС или более строгая изоляция.

### 4.2 Зачем нужен файл `.dockerignore` и к каким последствиям может привести его отсутствие?

`docker build` отправляет Docker-демону **контекст сборки** — содержимое каталога проекта, и инструкции `COPY` берут файлы из него. `.dockerignore` исключает из контекста всё, что не нужно внутри образа.

Без него:

- **Утечка секретов.** `COPY . .` унесёт в образ `.env` с паролями и папку `.git` со всей историей. Любой, кто скачает образ, сможет их достать.
- **Большой и медленный контекст.** В контекст попадают `.venv`, `node_modules`, логи, артефакты сборки — сотни мегабайт, которые передаются демону при каждой сборке.
- **Раздутый образ** с тестами, документацией и мусором.
- **Сломанный кэш слоёв.** Изменение любого лишнего файла (лог, файл IDE) меняет контекст и заставляет заново выполнять `COPY` и все шаги после него.
- **Неработающий образ.** Локальный `.venv` или `__pycache__`, собранные под другую ОС, могут перезаписать правильные файлы в образе.

В проекте в контекст сборки попадают только 24 файла `app/*.py` и `requirements.txt` — 28 КБ (проверено сборкой тестового образа с `COPY . /ctx`). Важная деталь: шаблоны в `.dockerignore` считаются от корня проекта, поэтому `__pycache__/` исключает только папку в корне; для вложенных нужно `**/__pycache__/`.

### 4.3 Что такое многоэтапная сборка (Multi-stage build) и какие преимущества она даёт?

Это `Dockerfile` с несколькими инструкциями `FROM`. Каждая начинает отдельный этап со своим базовым образом. На первом этапе (`builder`) ставятся инструменты сборки и зависимости и собирается результат. Финальный этап начинается с чистого минимального образа и командой `COPY --from=builder` забирает **только готовый результат**. Всё остальное с первого этапа в итоговый образ не попадает.

Преимущества:

- **Меньше размер.** Компиляторы, SDK, pip-кэш, исходники зависимостей остаются на этапе сборки. Для компилируемых языков (Go) образ уменьшается в разы: в финале только бинарник.
- **Безопасность.** Меньше пакетов — меньше уязвимостей и инструментов, которыми может воспользоваться злоумышленник; в образе нет компилятора.
- **Один `Dockerfile` вместо скриптов.** Сборка и упаковка описаны вместе и воспроизводимы на любой машине.
- **Кэш по этапам.** Этапы кэшируются независимо.

В проекте на этапе `builder` зависимости ставятся в `/opt/venv`, а финальный образ получает только это окружение и код `app/`.

### 4.4 Зачем в инструкциях `Dockerfile` разделять копирование файлов зависимостей (`go.mod`, `package.json`, `requirements.txt`) и копирование остального исходного кода?

Ради **кэша слоёв**. Каждая инструкция `Dockerfile` создаёт слой, и Docker пересобирает слой, только если изменилась сама инструкция или файлы, которые она копирует. Как только один слой пересобран, все следующие тоже выполняются заново.

- Если сначала `COPY . .`, а потом `pip install`, любая правка кода меняет слой `COPY` и заставляет заново скачивать и ставить все зависимости.
- Если сначала скопировать только `requirements.txt` и установить зависимости, а код — потом, при правке кода слой с зависимостями берётся из кэша, и пересобирается только быстрый `COPY app`.

Проверено на проекте: после правки `app/main.py` пересборка заняла 5,2 с, шаг `RUN pip install -r requirements.txt` помечен `CACHED`, заново выполнен только `COPY app ./app`. Зависимости меняются редко, код — постоянно, поэтому такой порядок экономит время на каждой сборке.

### 4.5 Какая разница между командой `EXPOSE` в `Dockerfile` и флагом `-p` при выполнении `docker run`?

- **`EXPOSE 8080`** — это **документация**: пометка в образе, что приложение внутри слушает порт 8080. Сама по себе она **ничего не открывает** — без `-p` до контейнера с хоста не достучаться. Её используют люди, читающие образ, и инструменты (`docker run -P` публикует все EXPOSE-порты на случайные порты хоста, Docker Compose и оркестраторы видят порт по умолчанию).
- **`-p 8080:8080`** — реальная **публикация порта**: Docker пробрасывает порт хоста (слева) на порт контейнера (справа). Номера могут отличаться: `-p 9090:8080` откроет приложение на `localhost:9090`.

`-p` работает и без `EXPOSE`, а `EXPOSE` без `-p` доступа снаружи не даёт. Внутри общей Docker-сети контейнеры обращаются друг к другу по внутренним портам без публикации.
