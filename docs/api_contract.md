# API контракты

В данном документе описываются основные REST‑эндпоинты, используемые во фронтенде и воркерах. Все маршруты имеют префикс `/v1` и возвращают ответы в формате JSON. Запросы на изменение данных должны выполняться c `Content-Type: application/json`.

## 1. Создание видео и получение URL для загрузки

`POST /v1/videos`

Создаёт новую запись о видео и генерирует presigned URL для загрузки файла непосредственно в хранилище. Сервер также возвращает уникальный `video_id` и `share_token`, который предоставляет доступ к результату без авторизации.

### Запрос

```json
{
  "filename": "ride.mp4",
  "content_type": "video/mp4",
  "size_bytes": 183742913
}
```

Параметр `size_bytes` необязателен, но может использоваться для ограничения размера.

### Ответ

```json
{
  "video_id": "a2b6c4c8-2c28-4b3c-8e3e-1c0f1e0a3a2c",
  "share_token": "st_4f3f2b1a8b...",
  "upload": {
    "method": "PUT",
    "url": "https://storage.local/raw/...presigned...",
    "headers": {
      "Content-Type": "video/mp4"
    },
    "object_key": "raw/a2b6c4c8.../original.mp4",
    "expires_in_sec": 3600
  },
  "limits": {
    "max_duration_sec": 120,
    "max_size_bytes": 500000000
  }
}
```

Клиент должен выполнить HTTP PUT на указанный URL с загружаемым файлом. После успешного завершения загрузки требуется вызвать `/v1/videos/{id}/complete-upload`.

## 2. Подтверждение загрузки

`POST /v1/videos/{video_id}/complete-upload`

Подтверждает успешную загрузку видео и запускает асинхронный пайплайн обработки. Запрос должен содержать `share_token` и может включать дополнительные данные клиента.

### Запрос

```json
{
  "share_token": "st_4f3f2b1a8b...",
  "client": {
    "user_agent": "Mozilla/5.0",
    "timezone": "Europe/Amsterdam"
  }
}
```

### Ответ

```json
{
  "video_id": "...",
  "status": "processing",
  "job_id": "c1c4b8f0-3aa2-4cb7-9fd8-2ef4c6e8f9a1",
  "pipeline_version": "mvp_v1",
  "stages": [
    {"name": "normalize", "status": "queued"},
    {"name": "pose", "status": "pending"},
    {"name": "features", "status": "pending"},
    {"name": "feedback", "status": "pending"}
  ]
}
```

Если видео уже было обработано или находится в обработке, сервер возвращает текущий статус, а не создаёт новую задачу.

## 3. Получение статуса и прогресса

`GET /v1/videos/{video_id}`

Возвращает статус обработки, процент выполнения по стадиям и ссылки на артефакты (при их наличии). Для доступа требуется `share_token` в query‑параметрах.

### Пример запроса

```
GET /v1/videos/a2b6c4c8-2c28-4b3c-8e3e-1c0f1e0a3a2c?share_token=st_4f3f2b1a8b...
```

### Пример ответа

```json
{
  "video_id": "a2b6c4c8-2c28-4b3c-8e3e-1c0f1e0a3a2c",
  "status": "processing",
  "pipeline_version": "mvp_v1",
  "progress": {
    "pct": 0.43,
    "stage": "pose",
    "stage_pct": 0.62,
    "eta_sec": null,
    "updated_at": "2026-01-07T10:58:12Z"
  },
  "stages": [
    {"name": "normalize", "status": "done", "started_at": "...", "ended_at": "..."},
    {"name": "pose", "status": "running", "started_at": "...", "ended_at": null},
    {"name": "features", "status": "pending", "started_at": null, "ended_at": null},
    {"name": "feedback", "status": "pending", "started_at": null, "ended_at": null}
  ],
  "artifacts": {
    "original": {"url": "...", "expires_in_sec": 900},
    "normalized": null,
    "keypoints": null,
    "features": null,
    "feedback": null
  },
  "errors": []
}
```

Когда видео обработано (`status = "done"`), поля `artifacts.normalized`, `artifacts.keypoints`, `artifacts.features`, `artifacts.feedback` будут заполнены presigned URL.

## 4. Получение артефактов

`GET /v1/videos/{video_id}/artifacts`

Удобный способ получить список артефактов и их версии. Возвращает массив элементов с указанием типа (`kind`), версии и presigned URL.

### Пример ответа

```json
{
  "video_id": "...",
  "artifacts": [
    {"kind": "normalized", "version": "v1", "url": "...", "expires_in_sec": 900},
    {"kind": "keypoints",   "version": "v1", "url": "...", "expires_in_sec": 900},
    {"kind": "features",    "version": "v1", "url": "...", "expires_in_sec": 900},
    {"kind": "feedback",    "version": "v1", "url": "...", "expires_in_sec": 900}
  ]
}
```

## 5. Отмена обработки (опционально)

`POST /v1/videos/{video_id}/cancel`

Отменяет текущую обработку. На уровне MVP эта ручка может отсутствовать, но рекомендуется заложить поддержку. При отмене воркеры должны проверять статус и корректно завершаться.

### Ответ

```json
{
  "video_id": "...",
  "status": "canceled"
}
```

## Статусы и стадии

- **video.status**: `created` → `uploaded` → `processing` → (`done` | `failed` | `canceled`).
- **stage.status**: `pending` (ещё не поставлена), `queued` (в очереди), `running` (в обработке), `done`, `failed`.

### Вес стадий для общего прогресса

Для расчёта общего процента выполнения используется весовая схема:

| Стадия      | Вес |
|-------------|-----|
| normalize   | 0.10|
| pose        | 0.70|
| features    | 0.10|
| feedback    | 0.10|

Общий прогресс `progress.pct` вычисляется как сумма произведения веса на процент выполнения текущей стадии. Например, если `pose` выполнена на 62 %, а остальные стадии завершены/не начаты, то прогресс = 0.1 + 0.62*0.7 = ~0.53.

### Идемпотентность

Ручки `POST /v1/videos` и `POST /v1/videos/{id}/complete-upload` должны быть идемпотентны. Повторный вызов не должен создавать дубликаты задач. Каждая стадия пайплайна также должна проверять существование целевого артефакта, чтобы избежать повторной обработки при перезапуске.

## Ошибки

API возвращает коды ошибок, соответствующие стандарту HTTP: `400` для некорректных запросов, `404` для отсутствующих ресурсов, `500` для внутренних ошибок сервера. Поле `errors` в ответе `/v1/videos/{id}` содержит подробности о сбоях стадии (если они произошли).

## Заключение

Этот API обеспечивает чёткий контракт между фронтендом, backend’ом и воркерами. Использование presigned URL разгружает API‑сервер, а статусы и прогресс дают пользователю прозрачность процесса. Контракт спроектирован так, чтобы его можно было расширять: добавлять новые стадии, новые типы артефактов и параметры версионирования без нарушения обратной совместимости.