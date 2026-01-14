---
name: План развития workers snowboard-app (Clean Architecture)
overview: План продолжения разработки workers и пайплайна обработки видео с опорой на Clean Architecture. Фазы 1-5 реализованы; фокус ниже - воркеры, надежность и масштабирование.
todos:
  - id: phase1-infra
    content: "Фаза 1: Инфраструктура и базовая настройка"
    status: done
  - id: phase2-db
    content: "Фаза 2: База данных и модели"
    status: done
  - id: phase3-storage
    content: "Фаза 3: Storage Backend"
    status: done
  - id: phase4-queue
    content: "Фаза 4: Очередь задач (Redis)"
    status: done
  - id: phase5-api
    content: "Фаза 5: Backend API через Use Cases"
    status: done
  - id: phase6-workers-common
    content: "Фаза 6: Workers Common (адаптеры + утилиты)"
    status: pending
  - id: phase7-transcode
    content: "Фаза 7: Transcode Worker (CPU)"
    status: pending
  - id: phase8-pose
    content: "Фаза 8: Pose Worker (GPU) + Triton adapter"
    status: pending
  - id: phase9-features
    content: "Фаза 9: Features Worker (CPU)"
    status: pending
  - id: phase10-feedback
    content: "Фаза 10: Feedback Worker (CPU)"
    status: pending
  - id: phase11-orchestration
    content: "Фаза 11: Оркестрация, надежность, идемпотентность"
    status: pending
  - id: phase12-observability
    content: "Фаза 12: Наблюдаемость, эксплуатация и оптимизация"
    status: pending
---

# План развития workers snowboard-app (Clean Architecture)

Этот план продолжает развитие **workers-пайплайна** с соблюдением Clean Architecture:
- доменная логика и переходы стадий живут в `backend/app/domain/` и `backend/app/application/`;
- воркеры - тонкие consumers: читают артефакты, вызывают use cases, публикуют результаты;
- инфраструктура (Redis, Postgres, Storage, Triton) скрыта за интерфейсами.

Фазы 1-5 считаются завершенными и служат базой для следующих шагов.

---

## Принципы для workers

1. **Снизу вверх**: инфраструктура и базовые зависимости перед бизнес-логикой.
2. **По зависимостям**: модули, от которых зависят другие — раньше.
3. **По пайплайну**: transcode → pose → features → feedback.
4. **Clean-lite границы**:
   - `domain/` и `application/` не импортируют FastAPI/SQLAlchemy/redis/boto3/tritonclient.
   - всё общение с внешним миром через **Interfaces**.
5. **Итеративно**: каждый этап должен быть тестируем отдельно.

---

## Target Architecture (Clean-lite)

### Слои и зависимости (внутрь)

- **Domain**: `AnalysisJob`, статусы/переходы, `ArtifactKind`, `Artifact`, `VideoStatus`.
- **Application (Use Cases)**: `StartAnalysis`, `HandleStageCompleted`, `FinalizeAnalysis`, `FailAnalysis`, (и read-only use cases для API: `GetStatus`, `ListArtifacts`).
- **Interfaces** (интерфейсы): `JobRepo`, `Queue`, `Storage`, `InferenceClient`, `Clock`.
- **Infrastructure**: реализации интерфейсов для Postgres/Redis/Storage/Triton.
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

- Реализовать `backend/app/presentation/bootstrap/settings.py` (Settings с pydantic-settings).
- Реализовать `backend/app/infrastructure/logging.py` (структурированное логирование).
- Реализовать `workers/common/config.py` (общая конфигурация для воркеров).
- Реализовать `workers/common/logging.py` (логирование для воркеров).

**Зависимости:** нет  
**Тестирование:** проверить чтение конфига и логирование.

---

## Фаза 2: База данных и модели

### 2.1 Модели данных

- Реализовать `backend/app/infrastructure/db/orm_models.py`:
  - `VideoDB` (id, status, etc.) - ORM модель с суффиксом DB
  - `JobStageDB` (video_id, name, status, started_at, ended_at) - ORM модель с суффиксом DB
  - `ArtifactDB` (video_id, kind, version, storage_path) - ORM модель с суффиксом DB
- Настроить `backend/app/infrastructure/db/session.py` (SQLAlchemy session factory).
- Создать миграции Alembic.

**Зависимости:** фаза 1.2  
**Тестирование:** создать тестовые записи, проверить CRUD.

### 2.2 Схемы API

- Реализовать `backend/app/presentation/api/schemas/videos.py`:
  - `CreateVideoRequest`, `CreateVideoResponse`
  - `VideoStatusResponse`, `ArtifactResponse`
- Валидация через Pydantic.

**Зависимости:** фаза 2.1  
**Тестирование:** сериализация/десериализация.

---

## Фаза 3: Storage Backend

### 3.1 Абстракция Storage (реализация интерфейса)

- Создать `backend/app/infrastructure/storage/base.py` (базовая абстракция для реализации интерфейса `Storage`).
- Реализовать `backend/app/infrastructure/storage/local.py` (Local storage для MVP).
- Реализовать `backend/app/infrastructure/storage/s3.py` (S3/MinIO storage для production).
- Интерфейс `Storage` определен в `application/interfaces/storage.py`.

**Зависимости:** фаза 1.2  
**Тестирование:** unit-тесты upload/download, создание директорий.

### 3.2 Storage для воркеров

- `workers/common/storage.py` использует тот же backend и совместимые ключи/пути.

**Зависимости:** фаза 3.1  
**Тестирование:** воркер читает/пишет файлы.

---

## Фаза 4: Очередь задач (Redis)

### 4.1 Redis клиент

- `backend/app/infrastructure/queue/redis_client.py` (подключение к Redis).
- `backend/app/infrastructure/queue/redis_queue.py` (реализация интерфейса `Queue` поверх RQ/Redis).

**Зависимости:** фаза 1.2  
**Тестирование:** подключение, постановка задач.

### 4.2 Регистрация задач

- `backend/app/presentation/workers/rq/tasks.py` (регистрация/декораторы для задач).
- `backend/app/presentation/workers/rq/worker_entrypoint.py` (точка входа воркеров).
- Очереди: `cpu` и `gpu`.

**Зависимости:** фаза 4.1  
**Тестирование:** запустить воркер, обработать тестовую задачу.

---

## Фаза 4.5: Clean-lite каркас (новая)

Цель: добавить “рельсы” архитектуры **до** активной разработки API и воркеров, без переписывания всего.

### 4.5.1 Структура пакетов

В `backend/app/` добавить:

- `domain/` - доменные модели и бизнес-логика
- `application/` - use cases и интерфейсы
- `application/interfaces/` - интерфейсы (Protocol) для зависимостей
- `infrastructure/` - реализации интерфейсов (DB, Storage, Queue, Clock)
- `presentation/` - API, контроллеры, воркеры, bootstrap

### 4.5.2 Domain (минимум)

- `domain/analysis_job.py`
  - `AnalysisJobStatus` (enum)
  - `Stage` (enum: TRANSCODE/POSE/FEATURES/FEEDBACK)
  - `AnalysisJob` (state machine, инварианты)
- `domain/value_objects.py`
  - `ArtifactKind` (enum: ORIGINAL, NORMALIZED, KEYPOINTS, FEATURES, FEEDBACK)
  - `Artifact` (value object: kind, version, storage_path)
  - `VideoStatus` (enum: CREATED, UPLOADED, PROCESSING, DONE, FAILED, CANCELED)

**Минимальные инварианты:**
- стадии завершаются по порядку;
- `SUCCEEDED` только после успешного `FEEDBACK`.

### 4.5.3 Interfaces (интерфейсы)

- `application/interfaces/job_repo.py`: `JobRepo`
- `application/interfaces/queue.py`: `Queue`
- `application/interfaces/storage.py`: `Storage`
- `application/interfaces/clock.py`: `Clock`
- `application/interfaces/uow.py`: `UnitOfWork`

(Интерфейс `InferenceClient` добавить в фазе 8.)

### 4.5.4 Composition root и Infrastructure

- `presentation/bootstrap/container.py`:
  - wiring реализаций интерфейсов (Postgres/Redis/Storage/Clock)
  - передача их в use cases
- `presentation/bootstrap/settings.py`: Settings с pydantic-settings
- `infrastructure/db/orm_models.py`: ORM модели (VideoDB, JobStageDB, ArtifactDB)
- `infrastructure/db/session.py`: SQLAlchemy session factory
- `infrastructure/db/migrations/`: Alembic миграции
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

**Важно:** use cases зависят только от `domain` и `interfaces`.

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

### 5.3 Infrastructure (реализации интерфейсов)

Сделать реализации интерфейсов:

- `infrastructure/db/job_repo.py` (JobRepo) - реализация через SQLAlchemy
- `infrastructure/db/video_repo.py` (VideoRepo) - реализация через SQLAlchemy
- `infrastructure/db/uow.py` (UnitOfWork) - реализация через SQLAlchemy session
- `infrastructure/queue/redis_queue.py` (Queue) - реализация через RQ/Redis
- `infrastructure/storage/local.py` и `infrastructure/storage/s3.py` (Storage)
- `infrastructure/clock/system_clock.py` (Clock)

**Примечание:** ORM модели находятся в `infrastructure/db/orm_models.py` с суффиксом DB (VideoDB, JobStageDB, ArtifactDB).

**Важно:** “progress/artifacts/model_registry” — это либо read-only use cases, либо часть adapter’ов, но не “services”.

### 5.4 Main application

- `backend/app/main.py` или `backend/app/presentation/api/routes/`:
  - подключение роутов
  - middleware (CORS, error handling)
  - создание контейнера зависимостей через `presentation/bootstrap/container.py`


---

## Фаза 6: Workers Common (адаптеры + утилиты)


**Цель:** унифицировать доступ к БД, Storage, контрактам и общим операциям для всех воркеров.

1. **Воркеры не принимают решений о статусах.** Только вызывают use cases (`HandleStageCompleted`, `FailAnalysis`).
2. **Не зависит от инфраструктуры в домене.** Воркеры зависят от адаптеров/портов, но не наоборот.
3. **Явные контракты артефактов.** Все вход/выходы валидируются через `schemas/` и `contracts/`.
4. **Идемпотентность по умолчанию.** Повторные задачи не должны ломать состояние.
### Задачи
- `backend/app/presentation/bootstrap/runtime.py` (get_session): подключение к БД для воркеров (read/write) и повторное использование настроек.
- `backend/app/presentation/bootstrap/runtime.py` (get_storage): единый клиент storage (local/S3), совместимый с API.
- `backend/app/presentation/workers/common/video_io.py`: чтение/запись видео, утилиты для ffmpeg (использует `storage_path` вместо `object_key`).
- `backend/app/presentation/workers/common/contracts.py`: загрузка контрактов модели и схем.
- `backend/app/presentation/workers/common/schemas.py`: валидация артефактов `keypoints_v1.jsonl`, `features_v1.json`, `feedback_v1.json`.
- `backend/app/presentation/workers/common/progress.py`: единый механизм прогресса/логирования этапов.

**Зависимости:** фазы 1-5.
**Готовность:** все воркеры используют одинаковые helpers и не дублируют логику.

---

## Фаза 7: Transcode Worker (CPU)

**Цель:** нормализовать видео и инициировать следующий этап пайплайна.

### Задачи
- `backend/app/presentation/workers/cpu/transcode/run.py`:
  - скачать оригинальное видео из storage по `storage_path`;
  - выполнить нормализацию (ffmpeg);
  - сохранить `normalized_video` в storage (используя `ArtifactKind.NORMALIZED`);
  - вызвать `HandleStageCompleted` со стадией `TRANSCODE` и артефактом (с `storage_path`).
- обработка ошибок через `FailAnalysis`.
- unit/smoke тест обработки малого видео.

**Зависимости:** фаза 6.
**Готовность:** при успехе задача `POSE` появляется в очереди через use case.

---

## Фаза 8: Pose Worker (GPU) + Triton adapter

**Цель:** inference позы и генерация keypoints.

### Задачи
- `application/interfaces/inference_client.py`: интерфейс для inference (если не добавлен ранее).
- `backend/app/presentation/workers/gpu/pose/triton_client.py`: реализация `InferenceClient`.
- `backend/app/presentation/workers/gpu/pose/preprocessing.py`: подготовка кадров/тензоров.
- `backend/app/presentation/workers/gpu/pose/postprocessing.py`: heatmaps -> keypoints, фильтры confidence.
- `backend/app/presentation/workers/gpu/pose/run.py`:
  - чтение нормализованного видео по `storage_path` из артефакта `ArtifactKind.NORMALIZED`;
  - inference батчами;
  - запись `keypoints_v1.jsonl` в storage;
  - вызов `HandleStageCompleted(stage=POSE, artifacts=[Artifact(kind=ArtifactKind.KEYPOINTS, version="v1", storage_path=...)])`.

**Зависимости:** фазы 6-7.
**Готовность:** при успехе очередь получает `FEATURES`.

---

## Фаза 9: Features Worker (CPU)

**Цель:** вычисление фич из keypoints.

### Задачи
- `backend/app/presentation/workers/cpu/features/run.py`:
  - чтение `keypoints_v1.jsonl` по `storage_path` из артефакта `ArtifactKind.KEYPOINTS`;
  - вычисление метрик и временных рядов;
  - запись `features_v1.json` в storage;
  - вызов `HandleStageCompleted(stage=FEATURES, artifacts=[Artifact(kind=ArtifactKind.FEATURES, version="v1", storage_path=...)])`.
- минимальная валидация и тест на sample данных.

**Зависимости:** фаза 8.
**Готовность:** при успехе очередь получает `FEEDBACK`.

---

## Фаза 10: Feedback Worker (CPU)

**Цель:** применение правил и генерация итогового фидбека.

### Задачи
- `backend/app/presentation/workers/cpu/feedback/run.py`:
  - чтение `features_v1.json` по `storage_path` из артефакта `ArtifactKind.FEATURES`;
  - загрузка `rules/feedback/v1.yaml`;
  - генерация `feedback_v1.json` в storage;
  - вызов `HandleStageCompleted(stage=FEEDBACK, artifacts=[Artifact(kind=ArtifactKind.FEEDBACK, version="v1", storage_path=...)])`.
- инициировать `FinalizeAnalysis` через use case (если не входит в `HandleStageCompleted`).

**Зависимости:** фаза 9.
**Готовность:** статус видео `completed`, все артефакты доступны через API.

---

## Фаза 11: Оркестрация, надежность, идемпотентность

**Цель:** стабильный пайплайн без побочных эффектов от повторов и с четкой обработкой ошибок.

### Задачи
- idempotency key для задач (`event_id`) + таблица `processed_events` в Postgres.
- защита от повторов в `HandleStageCompleted` и `FailAnalysis`.
- retry policy в очереди (RQ): backoff, max_retries.
- fail-fast при несоответствии версий артефактов (`pipeline_version`, `ruleset_version`).

**Зависимости:** фазы 6-10.
**Готовность:** повторные сообщения не создают дубликатов артефактов и не ломают статус.

---

## Фаза 12: Наблюдаемость, эксплуатация и оптимизация

**Цель:** управляемость и производительность пайплайна.

### Задачи
- метрики по стадиям (latency, throughput, errors) + health checks workers.
- логирование с correlation-id (video_id/job_id) во всех воркерах.
- лимиты очередей и worker autoscaling (опционально, k8s/terraform).
- оптимизация GPU батчинга, IO и хранения артефактов.
- обновление `docs/operations.md` и `README.md` по workers.

**Зависимости:** фазы 6-11.
**Готовность:** понятные SLO/алерты, документированные точки отказа.

---

## Диаграмма зависимостей (workers-фокус)

```mermaid
graph TD
    API[Фазы 1-5: База + API] --> Common[Фаза 6: Workers Common]
    Common --> Transcode[Фаза 7: Transcode]
    Transcode --> Pose[Фаза 8: Pose]
    Pose --> Features[Фаза 9: Features]
    Features --> Feedback[Фаза 10: Feedback]
    Feedback --> Reliability[Фаза 11: Надежность]
    Reliability --> Observability[Фаза 12: Наблюдаемость]
```
