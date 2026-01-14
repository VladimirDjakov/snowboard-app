---
name: План развития workers/ (Clean Architecture) после фазы 5
overview: План развития workers/ с учётом уже выполненных фаз 1–5 developer_plan2.md и принципов Clean Architecture. Фокус — единые use cases, порты/адаптеры, идемпотентность, наблюдаемость, тестируемость.
todos:
  - id: phase6-workers-common
    content: "Фаза 6: Общий слой воркеров (ports/adapters/utilities)"
    status: pending
  - id: phase7-transcode
    content: "Фаза 7: Transcode worker (CPU) через use case"
    status: pending
  - id: phase8-pose
    content: "Фаза 8: Pose worker (GPU) + Triton adapter"
    status: pending
  - id: phase9-features
    content: "Фаза 9: Features worker (CPU)"
    status: pending
  - id: phase10-feedback
    content: "Фаза 10: Feedback worker (CPU)"
    status: pending
  - id: phase11-ops
    content: "Фаза 11: Надёжность, идемпотентность, мониторинг"
    status: pending
  - id: phase12-integration
    content: "Фаза 12: Интеграция и end-to-end тесты"
    status: pending
---

# План развития workers/ (Clean Architecture)

> Контекст: первые 5 фаз из `developer_plan2.md` уже реализованы. Далее фокус на `workers/` и совместимости с Clean Architecture.  
> Рабочая идея: **воркеры не содержат бизнес-логики переходов** — они лишь читают артефакты, выполняют вычисления и вызывают use cases.

## Базовые принципы для workers/

1. **Thin worker**: минимум логики; оркестрация и переходы — в `application/use_cases/`.
2. **Ports & Adapters**: воркер взаимодействует с внешним миром только через адаптеры (Storage, DB, Queue, Inference).
3. **Единые use cases**: воркер вызывает те же `HandleStageCompleted/FailAnalysis`, что и API.
4. **Версионирование артефактов**: версия фиксируется в имени файлов и в БД; воркер не должен «угадывать» схему.
5. **Повторяемость и идемпотентность**: воркер может безопасно повторять задачу.
6. **Observability**: структурированные логи + метрики (latency, bytes, frames).

---

## Фаза 6: Общий слой воркеров (ports/adapters/utilities)

### 6.1 Конфигурация и зависимости
- Единый конфиг `workers/common/config.py` (путь storage, redis, db, triton, версии артефактов).
- Логирование `workers/common/logging.py` (структурировано; trace/job id).

### 6.2 Адаптеры, разделённые от логики воркеров
- `workers/common/storage.py`: ArtifactStore (должен совпадать с backend).
- `workers/common/db.py`: тонкий слой доступа к БД (только чтение/обновление в рамках use cases).
- `workers/common/queue.py`: publishing/ack (если часть вынесена из backend).
- `workers/common/contracts.py`: доступ к контрактам моделей/схем.

### 6.3 Базовые утилиты
- `workers/common/video_io.py`: чтение/запись/нормализация видео.
- `workers/common/schemas.py`: валидация артефактов по schemas/.
- `workers/common/telemetry.py`: базовые метрики/тайминги.

**Результат:** воркеры имеют единый «фреймворк» и одинаковый способ чтения артефактов/логирования.

---

## Фаза 7: Transcode worker (CPU)

### 7.1 Вход/выход
- Вход: original video из storage.
- Выход: `normalized.mp4`.

### 7.2 Поток
1. Скачать исходный файл.
2. Нормализовать `ffmpeg` (выравнивание FPS/разрешения).
3. Загрузить `normalized.mp4`.
4. Вызвать `HandleStageCompleted(stage=TRANSCODE, artifacts=[normalized])`.

### 7.3 Архитектурные правила
- Никакой постановки `POSE` напрямую — это делает use case.
- Все побочные эффекты (storage/queue) за границей domain/application.

---

## Фаза 8: Pose worker (GPU) + Triton adapter

### 8.1 Порт InferenceClient
- `application/ports/inference_client.py`: абстрактный клиент.
- Adapter: `workers/gpu/pose/triton_client.py`.

### 8.2 Pre/Post
- Pre: нарезка кадров, нормализация, batch.
- Post: heatmaps → keypoints, фильтрация confidence.

### 8.3 Поток
1. Скачать `normalized.mp4`.
2. Прогнать inference через Triton.
3. Сохранить `keypoints_v1.jsonl`.
4. Вызвать `HandleStageCompleted(stage=POSE, artifacts=[keypoints])`.

---

## Фаза 9: Features worker (CPU)

### 9.1 Поток
1. Скачать `keypoints_v1.jsonl`.
2. Посчитать временные ряды и агрегаты.
3. Сохранить `features_v1.json`.
4. Вызвать `HandleStageCompleted(stage=FEATURES, artifacts=[features])`.

### 9.2 Правило
- Фичи должны быть стабильны, deterministic, версионированы.

---

## Фаза 10: Feedback worker (CPU)

### 10.1 Поток
1. Скачать `features_v1.json`.
2. Применить `rules/feedback/v1.yaml`.
3. Сохранить `feedback_v1.json`.
4. Вызвать `HandleStageCompleted(stage=FEEDBACK, artifacts=[feedback])`.

### 10.2 Финализация
- `HandleStageCompleted` внутри use case может вызывать `FinalizeAnalysis`.

---

## Фаза 11: Надёжность, идемпотентность, мониторинг

### 11.1 Идемпотентность
- Ввести `processed_events` или `worker_runs` (event_id) в БД.
- Если событие уже обработано — worker завершает задачу как no-op.

### 11.2 Повторные попытки
- Политика retry в RQ + ограничение количества попыток.
- Явный `FailAnalysis` при исчерпании ретраев.

### 11.3 Observability
- Метрики: время обработки стадии, размер файлов, FPS.
- Логи: `video_id`, `stage`, `artifact_version`, `trace_id`.

---

## Фаза 12: Интеграция и end-to-end тесты

### 12.1 Контурные тесты
- Прогон полного pipeline локально.
- Проверка артефактов и статусов.

### 12.2 Негативные сценарии
- Ошибка в транскоде → `FailAnalysis`.
- Отсутствие модели Triton → корректный отказ.

### 12.3 Документация
- Обновить `docs/operations.md` с шагами дебага воркеров.
- Добавить советы по масштабированию (CPU/GPU очереди).

---

## Рекомендованная структура workers/ (после фаз 6–10)

```
workers/
  common/
    config.py
    logging.py
    storage.py
    db.py
    schemas.py
    telemetry.py
    video_io.py
    contracts.py
  queue/
    tasks.py
    rq_worker.py
  cpu/
    transcode/
      run.py
    features/
      run.py
    feedback/
      run.py
  gpu/
    pose/
      run.py
      triton_client.py
```

---

## Чек-лист качества для каждого воркера

- [ ] Статусы и переходы через use case.
- [ ] Явные версии артефактов.
- [ ] Идемпотентность (повтор не ломает состояние).
- [ ] Валидированные входные/выходные данные.
- [ ] Логи + метрики с job id.
- [ ] Есть unit-тесты для core-алгоритма.

---

## Следующие действия

1. Реализовать Phase 6 (общие утилиты) и «скелет» всех воркеров.
2. Поднять Transcode worker и довести до стабильного артефакта `normalized.mp4`.
3. После этого последовательно добавлять GPU pose, features и feedback.

