---
name: План разработки snowboard-app (Clean-lite)
overview: Поэтапный план разработки сервиса анализа видео с учётом зависимостей между модулями, последовательности пайплайна и внедрения Clean-lite (Hexagonal / Ports & Adapters) без оверхеда.
todos:
  - id: phase1-infra
    content: "Фаза 1: Настроить Docker, конфигурацию и логирование"
    status: pending
  - id: phase2-db
    content: "Фаза 2: Реализовать модели БД и схемы API"
    status: pending
  - id: phase3-storage
    content: "Фаза 3: Реализовать Storage Backend (локальная ФС)"
    status: pending
  - id: phase4-queue
    content: "Фаза 4: Настроить Redis очередь и регистрацию задач"
    status: done
  - id: phase4_5-clean-lite
    content: "Фаза 4.5: Внедрить Clean-lite каркас (Domain + Use Cases + Ports + Adapters + Composition)"
    status: pending
  - id: phase5-api
    content: "Фаза 5: Реализовать Backend API endpoints через Use Cases"
    status: pending
  - id: phase6-workers-common
    content: "Фаза 6: Реализовать общие утилиты и адаптеры для воркеров"
    status: pending
  - id: phase7-transcode
    content: "Фаза 7: Реализовать Transcode Worker (CPU) через Use Cases"
    status: pending
  - id: phase8-pose
    content: "Фаза 8: Реализовать Pose Inference Worker (GPU) + Triton adapter"
    status: pending
  - id: phase9-features
    content: "Фаза 9: Реализовать Features Worker (CPU) через Use Cases"
    status: pending
  - id: phase10-feedback
    content: "Фаза 10: Реализовать Feedback Worker (CPU) через Use Cases"
    status: pending
  - id: phase11-frontend
    content: "Фаза 11: Реализовать Frontend (React)"
    status: pending
  - id: phase12-integration
    content: "Фаза 12: Интеграция, тестирование, идемпотентность и оптимизация"
    status: pending
---

# План разработки snowboard-app (Clean-lite)

Обновлённый план разработки сервиса анализа видео катания на сноуборде с учётом **Clean-lite** подхода:  
**Hexagonal / Ports & Adapters + минимальный Domain + Use Cases**, без избыточной церемонии.

Цель — получить 90% ценности:
- доменная “истина” о статусах/стадиях и инвариантах живёт в `domain/`;
- оркестрация пайплайна (queue next stage, finalize/fail) живёт в `application/` (use cases);
- инфраструктура (Postgres/Redis/Storage/Triton/FastAPI) — в `adapters/`;
- API и воркеры тонкие: парсят вход, вызывают use case, маппят ответ/ошибки.

---

## Принципы разработки

1. **Снизу вверх**: инфраструктура и базовые зависимости перед бизнес-логикой.
2. **По зависимостям**: модули, от которых зависят другие — раньше.
3. **По пайплайну**: transcode → pose → features → feedback.
4. **Clean-lite границы**:
   - `domain/` и `application/` не импортируют FastAPI/SQLAlchemy/redis/boto3/tritonclient.
   - всё общение с внешним миром через **Ports**.
5. **Итеративно**: каждый этап должен быть тестируем отдельно.

---

## Target Architecture (Clean-lite)

### Слои и зависимости (внутрь)

- **Domain**: `AnalysisJob`, статусы/переходы, `VideoRef`, `ModelSignature`.
- **Application (Use Cases)**: `StartAnalysis`, `HandleStageCompleted`, `FinalizeAnalysis`, `FailAnalysis`, (и read-only use cases для API: `GetStatus`, `ListArtifacts`).
- **Ports** (интерфейсы): `JobRepo`, `Queue`, `ArtifactStore`, `InferenceClient`, `Clock`.
- **Adapters**: реализации портов для Postgres/Redis/Storage/Triton.
- **FastAPI + worker-consumers**: только вход/выход и вызов use cases.

---

## Фаза 1: Инфраструктура и базовая настройка

### 1.1 Docker и окружение

- Настроить `docker-compose.yml` (Postgres, Redis, без MinIO для MVP).
- Создать Dockerfile для API, CPU/GPU воркеров.
- Настроить `.env.example` с переменными окружения.
- Создать базовые скрипты (`dev_up.sh`, `dev_down.sh`).

**Файлы:** `infra/docker-compose.yml`, `infra/docker/*.Dockerfile`, `.env.example`

### 1.2 Конфигурация и логирование

- Реализовать `backend/app/composition/settings.py` (Settings с pydantic-settings).
- Реализовать `backend/app/infrastructure/logging.py` (структурированное логирование).
- Реализовать `workers/common/config.py` (общая конфигурация для воркеров).
- Реализовать `workers/common/logging.py` (логирование для воркеров).

**Зависимости:** нет  
**Тестирование:** проверить чтение конфига и логирование.

---

## Фаза 2: База данных и модели

### 2.1 Модели данных

- Реализовать `backend/app/infrastructure/postgres/orm_models.py`:
  - `Video` (id, status, etc.)
  - `JobStage` (video_id, name, status, started_at, ended_at)
  - `Artifact` (video_id, kind, version, object_key)
- Настроить `backend/app/infrastructure/postgres/session.py` (SQLAlchemy session factory).
- Создать миграции Alembic.

**Зависимости:** фаза 1.2  
**Тестирование:** создать тестовые записи, проверить CRUD.

### 2.2 Схемы API

- Реализовать `backend/app/api/schemas/videos.py`:
  - `CreateVideoRequest`, `CreateVideoResponse`
  - `VideoStatusResponse`, `ArtifactResponse`
- Валидация через Pydantic.

**Зависимости:** фаза 2.1  
**Тестирование:** сериализация/десериализация.

---

## Фаза 3: Storage Backend

### 3.1 Абстракция Storage (как Adapter, но можно начать сейчас)

- Создать `backend/app/adapters/storage/base.py` (реализация порта `ArtifactStore` или базовая абстракция).
- Реализовать `backend/app/adapters/storage/local_store.py` (Local storage для MVP).
- Реализовать `backend/app/adapters/storage/s3_store.py` (опционально).
- Фабрика `backend/app/adapters/storage/factory.py` (create store).

**Зависимости:** фаза 1.2  
**Тестирование:** unit-тесты upload/download, создание директорий.

### 3.2 Storage для воркеров

- `workers/common/storage.py` использует тот же backend и совместимые ключи/пути.

**Зависимости:** фаза 3.1  
**Тестирование:** воркер читает/пишет файлы.

---

## Фаза 4: Очередь задач (Redis)

### 4.1 Redis клиент

- `backend/app/adapters/redis/redis_client.py` (подключение к Redis).
- `backend/app/adapters/redis/queue.py` (реализация порта `Queue` поверх RQ/Redis).

**Зависимости:** фаза 1.2  
**Тестирование:** подключение, постановка задач.

### 4.2 Регистрация задач

- `workers/queue/tasks.py` (регистрация/декораторы для задач).
- `workers/queue/rq_worker.py` (точка входа воркеров).
- Очереди: `cpu` и `gpu`.

**Зависимости:** фаза 4.1  
**Тестирование:** запустить воркер, обработать тестовую задачу.

---

## Фаза 4.5: Clean-lite каркас (новая)

Цель: добавить “рельсы” архитектуры **до** активной разработки API и воркеров, без переписывания всего.

### 4.5.1 Структура пакетов

В `backend/app/` добавить:

- `domain/`
- `application/`
- `application/ports/`
- `adapters/` (частично уже начнётся в фазах 3–4)
- `composition/`

### 4.5.2 Domain (минимум)

- `domain/analysis_job.py`
  - `AnalysisJobStatus` (enum)
  - `Stage` (enum: TRANSCODE/POSE/FEATURES/FEEDBACK)
  - `AnalysisJob` (state machine, инварианты)
- `domain/value_objects.py`
  - `VideoRef`
  - `ModelSignature`

**Минимальные инварианты:**
- стадии завершаются по порядку;
- `SUCCEEDED` только после успешного `FEEDBACK`.

### 4.5.3 Ports (интерфейсы)

- `application/ports/job_repo.py`: `JobRepo`
- `application/ports/queue.py`: `Queue`
- `application/ports/artifact_store.py`: `ArtifactStore`
- `application/ports/clock.py`: `Clock`
- `application/ports/uow.py`: `UnitOfWork`

(Порт `InferenceClient` добавить в фазе 8.)

### 4.5.4 Composition root и Infrastructure

- `composition/container.py`:
  - wiring адаптеров (Postgres/Redis/Storage/Clock)
  - передача их в use cases
- `composition/settings.py`: Settings с pydantic-settings
- `infrastructure/postgres/orm_models.py`: ORM модели
- `infrastructure/postgres/session.py`: SQLAlchemy session factory
- `infrastructure/postgres/migrations/`: Alembic миграции
- `infrastructure/logging.py`: структурированное логирование

**Тестирование:** import-check: domain/application не тянут инфраструктурные импорты.

---

## Фаза 5: Backend API (через Use Cases)

### 5.0 Use Cases (новый обязательный подпункт)

В `application/use_cases/`:

- `start_analysis.py` → `StartAnalysis`
- `get_status.py` → `GetAnalysisStatus` (read-only, нужен API)
- `list_artifacts.py` → `ListArtifacts` (read-only)
- `handle_stage_completed.py` → `HandleStageCompleted` (понадобится воркерам)
- `finalize_analysis.py` → `FinalizeAnalysis`
- `fail_analysis.py` → `FailAnalysis`

**Важно:** use cases зависят только от `domain` и `ports`.

### 5.1 Health checks

- `GET /health`
- `GET /health/ready` (readiness: БД, Redis, Storage через adapters)

**Зависимости:** 2.1, 3.1, 4.1

### 5.2 Основные API endpoints

- `POST /v1/videos` (создание видео, генерация upload URL/ключа)
- `POST /v1/videos/{id}/complete-upload` (вызывает `StartAnalysis`)
- `GET /v1/videos/{id}` (вызывает `GetAnalysisStatus`)
- `GET /v1/videos/{id}/artifacts` (вызывает `ListArtifacts`)

Локальный storage:
- `GET /api/v1/files/{key}` (скачивание)
- `PUT /api/v1/files/upload` (загрузка)

**Зависимости:** 2.1, 2.2, 3.1, 4.1, 5.0

### 5.3 Adapters (вместо backend/app/services/*)

Сделать реализации портов:

- `adapters/postgres/job_repo.py` (JobRepo)
- `adapters/postgres/uow.py` (UnitOfWork)
- `adapters/redis/queue.py` (Queue)
- `adapters/storage/artifact_store.py` (ArtifactStore)
- `adapters/clock/system_clock.py` (Clock)

**Примечание:** ORM модели находятся в `infrastructure/postgres/orm_models.py`, а не в adapters.

**Важно:** “progress/artifacts/model_registry” — это либо read-only use cases, либо часть adapter’ов, но не “services”.

### 5.4 Main application

- `backend/app/main.py`:
  - подключение роутов
  - middleware (CORS, error handling)
  - создание контейнера зависимостей (composition)

---

## Фаза 6: Workers Common (адаптеры + утилиты)

### 6.1 Общие утилиты

- `workers/common/db.py` (подключение к БД для воркеров)
- `workers/common/storage.py` (ArtifactStore backend)
- `workers/common/video_io.py` (видео I/O)
- `workers/common/contracts.py` (чтение контрактов модели)
- `workers/common/schemas.py` (валидация артефактов)

**Важно:** воркеры не должны сами решать переходы статусов — они вызывают use cases.

**Зависимости:** 2.1, 3.2, 4.1, 5.0  
**Тестирование:** unit-тесты утилит.

---

## Фаза 7: Worker Transcode (CPU) через Use Case

### 7.1 Transcode Worker

- `workers/cpu/transcode/run.py`:
  - чтение оригинального видео из storage
  - нормализация через ffmpeg
  - сохранение `normalized.mp4`
  - затем вызвать `HandleStageCompleted(job_id, stage=TRANSCODE, artifacts=[...])`

**Важно:** постановку `POSE` в очередь делает use case, а не воркер.

**Зависимости:** 6.1, 5.0  
**Тестирование:** обработать тестовое видео, проверить `normalized.mp4` и переход статуса.

---

## Фаза 8: Pose Inference (GPU) + Triton adapter

### 8.0 Добавить Port `InferenceClient`

- `application/ports/inference_client.py`: `InferenceClient` (run_pose / health / model_ready)

### 8.1 Triton Client (Adapter)

- `workers/gpu/pose/triton_client.py` → реализация `InferenceClient`
- проверка доступности модели, чтение контракта

### 8.2 Preprocessing и Postprocessing

- preprocessing: нарезка кадров, нормализация, подготовка тензоров
- postprocessing: heatmaps → keypoints, фильтрация confidence, нормализация

### 8.3 Pose Worker

- читает `normalized.mp4`
- делает inference батчами
- пишет `keypoints_v1.jsonl`
- на успех: `HandleStageCompleted(stage=POSE, artifacts=[keypoints...])`
- на ошибку: `FailAnalysis(stage=POSE, reason=...)`

**Важно:** постановку `FEATURES` делает use case.

---

## Фаза 9: Features Worker (CPU) через Use Case

### 9.1 Features Worker

- читает `keypoints_v1.jsonl`
- вычисляет метрики, сглаживание, агрегация
- пишет `features_v1.json`
- вызывает `HandleStageCompleted(stage=FEATURES, artifacts=[features...])`

**Важно:** постановку `FEEDBACK` делает use case.

---

## Фаза 10: Feedback Worker (CPU) через Use Case

### 10.1 Feedback Worker

- читает `features_v1.json`
- читает правила `rules/feedback/v1.yaml`
- генерирует `feedback_v1.json`
- вызывает `HandleStageCompleted(stage=FEEDBACK, artifacts=[feedback...])`
- `FinalizeAnalysis` может вызываться внутри `HandleStageCompleted` автоматически, когда stage=FEEDBACK.

---

## Фаза 11: Frontend (React)

### 11.1 API Client

- `frontend/src/lib/api.ts` типизированный клиент

### 11.2 Компоненты

- VideoPlayer
- PoseCanvasOverlay (keypoints jsonl)
- FeedbackPanel (feedback json)

### 11.3 Страницы

- Upload
- VideoResult (интеграция компонентов)

---

## Фаза 12: Интеграция, надёжность, тестирование, оптимизация

### 12.1 End-to-end тестирование

- полный пайплайн загрузки и обработки
- проверка ошибок
- проверка повторов сообщений

### 12.2 Идемпотентность (минимальный обязательный шаг)

- у каждого сообщения в очереди есть `event_id`
- воркер ведёт `processed_events` (таблица в Postgres) и игнорирует повторы
- `FailAnalysis` и `HandleStageCompleted` должны быть идемпотентны

*(Outbox можно добавить позже, как улучшение.)*

### 12.3 Оптимизация

- батчинг GPU воркера
- оптимизация запросов к БД
- кэширование/переиспользование артефактов по checksum (опционально)

### 12.4 Документация

- обновить README
- примеры API
- документировать формат правил feedback

---

## Диаграмма зависимостей (обновлённая)

```mermaid
graph TD
    Infra[Фаза 1: Инфраструктура] --> DB[Фаза 2: БД и модели]
    Infra --> Storage[Фаза 3: Storage]
    Infra --> Queue[Фаза 4: Очередь]

    Queue --> CleanLite[Фаза 4.5: Clean-lite каркас]
    DB --> CleanLite
    Storage --> CleanLite

    CleanLite --> API[Фаза 5: API через Use Cases]
    API --> WorkersCommon[Фаза 6: Workers Common]

    WorkersCommon --> Transcode[Фаза 7: Transcode]
    Transcode --> Pose[Фаза 8: Pose]
    Pose --> Features[Фаза 9: Features]
    Features --> Feedback[Фаза 10: Feedback]

    API --> Frontend[Фаза 11: Frontend]

    Feedback --> Integration[Фаза 12: Интеграция + идемпотентность]
    Frontend --> Integration
