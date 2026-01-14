# 🏂 Сервис анализа видео‑катания на сноуборде

Этот репозиторий содержит прототип сервиса анализа видео‑катания на сноуборде.

## 🚀 Быстрый старт

Для локального запуска проекта выполните следующие шаги:

### 1. Создайте конфигурацию на основе примера
```bash
cp .env.example .env
```

**Примечание:** По умолчанию используется локальная файловая система для хранения артефактов (рекомендуется для MVP). Файлы будут храниться в `runtime/storage/`. Для использования S3/MinIO измените `STORAGE_BACKEND=s3` в `.env` и раскомментируйте MinIO в `docker-compose.yml`.

### 2. Поднимите все сервисы
```bash
make dev-up
```

**Примечание:** MinIO не запускается по умолчанию (опционален). Для MVP на личном ПК локальная ФС проще и быстрее.

### 3. Скачайте и распакуйте модель для Triton
```bash
make pull-models
```

### 4. Выполните миграции базы данных
```bash
make migrate
```

### 5. Запустите тесты (опционально)
```bash
make test
```

---

## 🧪 Ручное тестирование API

Ниже — два способа поднять API и руками проверить основные эндпоинты.

### Вариант 1 (рекомендуется): поднять всё через Docker Compose

1) **Проверить, что API живое**

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/health/ready
```

2) **Открыть Swagger UI**

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

3) **Пример ручного теста эндпоинтов видео**

Создать видео:

```bash
curl -i -X POST "http://localhost:8000/v1/videos" \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.mp4","content_type":"video/mp4","size_bytes":12345}'
```

Из ответа возьмите `video_id`, `share_token` и `upload.url`.

Загрузить файл по `upload.url` (пример с локальным файлом `./test.mp4`):

```bash
curl -i -X PUT "<upload_url>" \
  -H "Content-Type: video/mp4" \
  --data-binary "@test.mp4"
```

Завершить загрузку:

```bash
curl -i -X POST "http://localhost:8000/v1/videos/<video_id>/complete-upload" \
  -H "Content-Type: application/json" \
  -d '{"share_token":"<share_token>"}'
```

Получить статус:

```bash
curl -i "http://localhost:8000/v1/videos/<video_id>?share_token=<share_token>"
```

Получить артефакты:

```bash
curl -i "http://localhost:8000/v1/videos/<video_id>/artifacts?share_token=<share_token>"
```

### Вариант 2: поднять только API локально (без Docker), но с поднятыми зависимостями

1) **Поднять Postgres/Redis**

```bash
docker compose -f infra/docker-compose.yml up -d postgres redis
```

2) **Запустить API локально через uvicorn** (из корня репо)

```bash
uv run --directory backend uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Важно: при этом `DATABASE_URL`/`REDIS_URL` должны указывать на `localhost`, а не на `postgres`/`redis` (как внутри compose). Проще всего — выставить их в окружении перед запуском или в `.env`.

---

## 📊 Диаграммы архитектуры

### Общий пайплайн обработки видео

```
┌──────────────────┐    Upload Complete    ┌──────────────────┐
│ 📤 Загрузка видео│ ───────────────────>  │ 🎬 Transcode      │
│                  │                       │ Нормализация     │
└──────────────────┘                       └────────┬─────────┘
                                                    │ Normalized Video
                                                    ▼
┌──────────────────┐    Keypoints          ┌───────────────────┐
│ 📊 Feature       │ <───────────────────  │ 🧠 Pose tracking   │
│ Extraction       │                       │                   │
└────────┬─────────┘                       └───────────────────┘
         │ Features
         ▼                                         
┌──────────────────┐    Complete          ┌────────────────────┐
│ 🧾 Rule-based    │ ──────────────────>  │ ✅ Готово           │
│ Feedback         │                      │                    │
│ Генерация фидбека│                      └────────────────────┘
└──────────────────┘
```

### Детальный пайплайн обработки

#### Этап 1: Загрузка видео

```
👤 Пользователь
    │
    │ Загрузка видео
    ▼
⚛️ Frontend ──POST /videos──> 🚀 API ──Создание записи──> 🗄️ Database
    │                              │
    │                              │ Генерация presigned URL
    │                              ▼
    │                        📦 Storage
    │                              │
    │                              │ Presigned URL
    │<─────────────────────────────┘
    │
    │ Прямая загрузка видео
    ▼
📦 Storage

⚛️ Frontend ──POST /complete──> 🚀 API ──Постановка задачи──> 📮 Queue
    │                              │
    │ Статус: processing           │
    │<─────────────────────────────┘
```

#### Этап 2: Обработка (воркеры)

```
📮 Queue ──Задача transcode──> 💻 Transcode Worker
                                      │
                                      ├─> 📦 Storage (чтение видео)
                                      ├─> 📦 Storage (сохранение normalized.mp4)
                                      ├─> 🗄️ Database (обновление статуса)
                                      └─> 📮 Queue (задача pose)

📮 Queue ──Задача pose──> 🎮 Pose Worker
                              │
                              ├─> 📦 Storage (чтение normalized.mp4)
                              ├─> 🧠 Triton (inference)
                              ├─> 📦 Storage (сохранение keypoints_v1.jsonl)
                              ├─> 🗄️ Database (обновление статуса)
                              └─> 📮 Queue (задача features)

📮 Queue ──Задача features──> 💻 Features Worker
                                   │
                                   ├─> 📦 Storage (чтение keypoints_v1.jsonl)
                                   ├─> 📊 Вычисление фич
                                   ├─> 📦 Storage (сохранение features_v1.json)
                                   ├─> 🗄️ Database (обновление статуса)
                                   └─> 📮 Queue (задача feedback)

📮 Queue ──Задача feedback──> 💻 Feedback Worker
                                  │
                                  ├─> 📦 Storage (чтение features_v1.json)
                                  ├─> 🧾 Применение правил
                                  ├─> 📦 Storage (сохранение feedback_v1.json)
                                  └─> 🗄️ Database (статус: completed)
```

#### Этап 3: Получение результата

```
⚛️ Frontend ──GET /status──> 🚀 API ──Чтение статуса──> 🗄️ Database
    │                                               │
    │      Статус: completed                        │
    │<──────────────────────────────────────────────┘

⚛️ Frontend ──GET /artifacts──> 🚀 API ──Генерация URLs──> 📦 Storage
    │                                                         │
    │       Presigned URLs артефактов                         │
    │<────────────────────────────────────────────────────────┘
    │
    │ Загрузка артефактов
    ▼
⚛️ Frontend ──Отображение результата──> 👤 Пользователь
```

---

## 🔖 Версионирование

Для обеспечения воспроизводимости результатов каждое видео обрабатывается определённой версией пайплайна. В таблице ниже перечислены основные сущности и их версии:

| Сущность | Описание |
|----------|----------|
| `pipeline_version` | Версия конвейера (transcode → pose → …) |
| `model_version` | Версия модели позы, развёрнутой в Triton |
| `features_version` | Версия схемы вычисляемых фич |
| `ruleset_version` | Версия набора rule‑based правил фидбека |

Версии фиксируются в базе данных (`videos.pipeline_version` и др.), а также в имени артефактов (например, `keypoints_v1.jsonl`).

---

## 📁 Структура репозитория

Ниже приведён обзор ключевых каталогов и файлов:

### 📚 `docs/` — документация

- **`architecture.md`** — подробные диаграммы и принятые решения
- **`api_contract.md`** — описание REST API и примеры запросов
- **`data_formats.md`** — схемы форматов `keypoints_v1.jsonl`, `features_v1.json`, `feedback_v1.json`
- **`operations.md`** — runbook (что делать, если не стартует Triton, очередь растёт и т. д.)
- **`adr/`** — архитектурные решения (почему Redis, JSONL, artifact store)

### 🏗️ `infra/` — инфраструктура и локальный запуск

- **`docker-compose.yml`** — описание сервисов (Postgres, Redis, MinIO, Triton, API, воркеры, фронтенд)
- **`docker/`** — Dockerfile для API, CPU/GPU‑воркеров и фронтенда
- **`scripts/`** — сервисные скрипты (`dev_up.sh`, `dev_down.sh`, `init_minio.sh`, `pull_models.sh`, `verify_sha256.sh`)
- **`k8s/`, `terraform/`** — зарезервированы для дальнейшего деплоя

### 💾 `runtime/` — локальные артефакты (не коммитить)

- **`triton_model_repository/`** — распакованный репозиторий моделей Triton
- **`cache/`** — кеш скачиваний (опционально)

### 📋 `contracts/` — контракт модели

- **`pose/pose_contract_v1.json`** — описание входных/выходных тензоров, нормализации и порядка суставов
- **`pose/skeleton_mapping_v1.yaml`** — список суставов и описание костей для отрисовки
- **`pose/examples/`** — маленькие примеры для smoke‑тестов

### 🎨 `frontend/` — клиентское приложение (React)

- **`pages/Upload.tsx`** — страница загрузки видео
- **`pages/VideoResult.tsx`** — страница просмотра результата
- **`components/VideoPlayer.tsx`** — видеоплеер
- **`components/PoseCanvasOverlay.tsx`** — слой отрисовки позы поверх видео
- **`components/FeedbackPanel.tsx`** — отображение rule‑based фидбека
- **`lib/api.ts`** — типизированный клиент API

### 🔧 `backend/` — FastAPI‑приложение (Clean Architecture)

- **`app/main.py`** — точка входа, подключение маршрутов и middleware
- **`app/api/routes/videos.py`** — эндпоинты для создания видео, завершения загрузки, получения статуса и артефактов
- **`app/api/schemas/`** — Pydantic‑схемы (DTO)
- **`app/domain/`** — доменные модели и бизнес-правила (AnalysisJob, ValueObjects)
- **`app/application/use_cases/`** — use cases для оркестрации бизнес-логики
- **`app/application/ports/`** — интерфейсы (Protocol) для зависимостей
- **`app/adapters/`** — реализации портов (PostgresJobRepo, RedisQueue, StorageArtifactStore)
- **`app/infrastructure/postgres/`** — ORM модели (Video, JobStage, Artifact), сессии и миграции (Alembic)
- **`app/infrastructure/logging.py`** — структурированное логирование
- **`app/composition/`** — dependency injection (Container, Settings)

### ⚙️ `workers/` — асинхронные воркеры

- **`common/`** — общие утилиты: конфиг, логирование, работа с хранилищем, обновление прогресса
- **`queue/`** — регистрация задач и точка входа для RQ‑воркеров
- **`cpu/transcode/`** — нормализация видео с помощью ffmpeg
- **`gpu/pose/`** — нарезка видео, вызов Triton, сохранение keypoints
- **`cpu/features/`** — вычисление временных рядов и углов
- **`cpu/feedback/`** — применение rule‑based правил

### 📜 `rules/` — наборы правил фидбека

- **`feedback/v1.yaml`** — версия v1 с порогами, текстами и временными диапазонами

### 📐 `schemas/` — JSON Schema для артефактов

Используются в тестах и дебаге.

### 🔄 `ci/` — конфигурация CI/CD

Конфигурация для lint, test, сборки образов.

---

## 📦 Артефакты обработки

После обработки видео создаются следующие файлы:

| Файл | Описание |
|------|----------|
| `normalized.mp4` | Нормализованное видео |
| `keypoints_v1.jsonl` | Ключевые точки на каждом кадре (по строкам) |
| `features_v1.json` | Агрегированные метрики и временные ряды |
| `feedback_v1.json` | Результат применения правил |

Для просмотра результата фронтенд загружает эти файлы по presigned URL и строит оверлей поз и панель фидбека.

---

## 🔧 Дополнительные материалы

### Запуск Triton и загрузка моделей

Скрипт `pull_models.sh` скачивает архив модели (из S3/MinIO/репозиториев artefact store), проверяет контрольную сумму и распаковывает репозиторий модели в `runtime/triton_model_repository`.

### Развитие проекта

Эта структура позволяет быстро развивать MVP до полноценного продукта: добавлять новые стадии пайплайна, менять модели, вводить ML‑фидбек, масштабировать сервисы и адаптировать инфраструктуру.
