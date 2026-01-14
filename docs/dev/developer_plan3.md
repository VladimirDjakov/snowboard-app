---
name: План развития workers/ (Clean Architecture)
overview: План продолжения разработки после реализации фаз 1–5 из developer_plan2.md, с упором на развитие воркеров в рамках Clean Architecture (ports/use cases/adapters).
todos:
  - id: phase1-5-done
    content: "Фазы 1–5 из developer_plan2.md реализованы (инфра, БД, storage, очередь, clean-lite, API)."
    status: done
  - id: phase6-workers-foundation
    content: "Фаза 6: Базовый каркас workers/ (ports, use cases orchestration, общие утилиты, совместимость с backend)."
    status: pending
  - id: phase7-transcode-worker
    content: "Фаза 7: CPU Transcode worker через use case (HandleStageCompleted/FailAnalysis)."
    status: pending
  - id: phase8-pose-worker
    content: "Фаза 8: GPU Pose worker + Triton adapter и порт InferenceClient."
    status: pending
  - id: phase9-features-worker
    content: "Фаза 9: CPU Features worker через use case."
    status: pending
  - id: phase10-feedback-worker
    content: "Фаза 10: CPU Feedback worker через use case."
    status: pending
  - id: phase11-workers-robustness
    content: "Фаза 11: Надежность, идемпотентность, наблюдаемость воркеров."
    status: pending
  - id: phase12-ops-scaling
    content: "Фаза 12: Операционная зрелость и масштабирование workers/."
    status: pending
---

# План развития workers/ (Clean Architecture)

Ниже — обновлённый план развития `workers/` после реализации фаз 1–5, с фокусом на чистую архитектуру и минимальный coupling между доменом, use cases и инфраструктурой.

## Ключевые принципы для workers/ в Clean Architecture

1. **Workers — это delivery/edge**: они лишь читают вход, вызывают use case, сохраняют артефакт и сообщают о результате. Они не управляют бизнес‑переходами напрямую.
2. **Use cases — источник правды**: постановка следующей стадии и обновление статусов — только через use case (`HandleStageCompleted`, `FailAnalysis`).
3. **Единые порты и модели домена**: workers используют те же `ports` и `domain` контракты, что и API.
4. **Чистые зависимости**:
   - `workers/*` могут импортировать `backend/app/application` и `backend/app/domain`.
   - `backend/app/domain` и `backend/app/application` **не** импортируют код воркеров.
5. **Артефакты — контракт**: версии артефактов и форматы фиксируются в `contracts/` и `schemas/`.

---

## Фаза 6: Базовый каркас workers/ (foundation)

### 6.1 Общие порты/адаптеры и инфраструктура

- Убедиться, что workers используют существующие `application/ports` и `domain` из `backend/`.
- Реализовать/добавить в `workers/common/`:
  - `db.py` — доступ к БД (reuse `backend/app/infrastructure/postgres/session.py`).
  - `storage.py` — тот же backend хранения, что у API (Local/S3).
  - `queue.py` — publish/ack через общий port `Queue` (если воркеры что-то планируют).
  - `logging.py` — единое структурированное логирование.
  - `config.py` — конфиг для воркеров (using same env vars as backend).

### 6.2 Use case wrappers

- В каждом воркере держать тонкий слой, который:
  1) валидирует вход (id, expected artifacts),
  2) загружает нужные файлы,
  3) вызывает use case,
  4) сохраняет артефакт(ы).

### 6.3 Контракты артефактов

- Валидация через `schemas/` и `contracts/`.
- Обязательное логирование версии `pipeline_version`, `model_version`, `features_version`, `ruleset_version`.

**Выход:** единый фундамент для последующих воркеров, общие утилиты и гарантии совместимости.

---

## Фаза 7: CPU Transcode worker

### 7.1 Технические шаги

- `workers/cpu/transcode/run.py`:
  - загрузка оригинального видео;
  - нормализация в `normalized.mp4` (ffmpeg);
  - сохранение артефакта в storage;
  - вызов `HandleStageCompleted(stage=TRANSCODE, artifacts=[normalized.mp4])`.

### 7.2 Инварианты

- Воркер не ставит в очередь `POSE` — это делает use case.
- Все ошибки идут через `FailAnalysis(stage=TRANSCODE, reason=...)`.

**Выход:** нормализованное видео и корректный переход к следующей стадии.

---

## Фаза 8: GPU Pose worker + Triton adapter

### 8.1 Порт `InferenceClient`

- Добавить/расширить порт в `backend/app/application/ports`.
- Реализация в `workers/gpu/pose/triton_client.py`.

### 8.2 Pre/Post-processing

- Нарезка и нормализация кадров.
- Преобразование heatmaps → keypoints.
- Сохранение `keypoints_v1.jsonl`.

### 8.3 Интеграция с use cases

- `HandleStageCompleted(stage=POSE, artifacts=[keypoints_v1.jsonl])`.
- Ошибки → `FailAnalysis`.

**Выход:** артефакт keypoints, корректный переход к Features.

---

## Фаза 9: CPU Features worker

### 9.1 Вычисление фич

- Загрузка `keypoints_v1.jsonl`.
- Вычисление метрик/рядов, агрегация.
- Сохранение `features_v1.json`.

### 9.2 Интеграция

- `HandleStageCompleted(stage=FEATURES, artifacts=[features_v1.json])`.

**Выход:** артефакт features, корректный переход к Feedback.

---

## Фаза 10: CPU Feedback worker

### 10.1 Генерация фидбека

- Загрузка `features_v1.json`.
- Применение `rules/feedback/v1.yaml`.
- Сохранение `feedback_v1.json`.

### 10.2 Финализация

- `HandleStageCompleted(stage=FEEDBACK, artifacts=[feedback_v1.json])`.
- Use case должен финализировать анализ (status=completed).

**Выход:** итоговый фидбек и завершение пайплайна.

---

## Фаза 11: Надёжность, идемпотентность, наблюдаемость

### 11.1 Идемпотентность

- Ввести `processed_events` или аналог на уровне use cases.
- `HandleStageCompleted` и `FailAnalysis` должны быть idempotent.

### 11.2 Наблюдаемость

- Стандартизировать метрики (duration, error rate, queue lag).
- Логи: correlation_id, video_id, stage, artifact_version.

### 11.3 Ретраи и DLQ

- Явные политики retry на уровне RQ.
- Dead-letter queue для отладок.

---

## Фаза 12: Операционная зрелость и масштабирование

- Масштабирование воркеров по очередям (cpu/gpu).
- Разделение resource pools (GPU vs CPU).
- Кеширование артефактов и reuse по checksum.
- Нагрузочные тесты пайплайна.

---

## Итог

Этот план закрепляет **чистую архитектуру** вокруг `workers/`: доменные правила и оркестрация остаются в `application`/`domain`, а воркеры — тонкие исполнители, работающие через порты. Это позволяет безопасно добавлять новые стадии или версии моделей без разрастания связности.
