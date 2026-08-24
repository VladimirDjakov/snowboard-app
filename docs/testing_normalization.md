## Проверка нормализации видео (артефакт в storage)

Ниже — минимальный сценарий, чтобы отправить видео через API и убедиться, что `normalized.mp4` появился в хранилище.

### 1) Поднять сервисы
```bash
make dev-up
make migrate
```

### 2) Создать видео и загрузить файл
```bash
curl -s -X POST "http://localhost:8000/v1/videos" \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.mp4","content_type":"video/mp4","size_bytes":12345}'
```

Из ответа возьми:
- `video_id`
- `share_token`
- `upload.url`

Загрузить файл:
```bash
curl -i -X PUT "<upload_url>" \
  -H "Content-Type: video/mp4" \
  --data-binary "@./test.mp4"
```

Завершить загрузку:
```bash
curl -i -X POST "http://localhost:8000/v1/videos/<video_id>/complete-upload" \
  -H "Content-Type: application/json" \
  -d '{"share_token":"<share_token>"}'
```

### 3) Дождаться обработки
Проверь статус:
```bash
curl -s "http://localhost:8000/v1/videos/<video_id>?share_token=<share_token>"
```

Статус должен стать `processing` → `completed` (после транскода).

### 4) Проверить normalized.mp4 в локальном storage
Если используется локальный storage, путь будет таким:
```
runtime/storage/proc/<video_id>/normalized.mp4
```

Проверка внутри контейнера:
```bash
docker compose -f infra/docker-compose.yml exec -T api \
  ls -la /app/runtime/storage/proc/<video_id>/normalized.mp4
```

Альтернатива — проверить артефакты через API:
```bash
curl -s "http://localhost:8000/v1/videos/<video_id>/artifacts?share_token=<share_token>"
```

Примечание: если используешь S3/MinIO, `normalized.mp4` будет в бакете по ключу
`proc/<video_id>/normalized.mp4`.
