# Работа с базой данных

Руководство по работе с базой данных: локальное тестирование и миграции в production.

## Локальная разработка

### Быстрая проверка

```bash
# 1. Поднять БД
make dev-up

# 2. Применить миграции
make migrate

# 3. Запустить тесты
make test
```

### Интерактивное тестирование

```bash
# Интерактивный Python скрипт
cd backend
uv run python scripts/test_db_manual.py

# Прямое подключение к PostgreSQL
docker exec -it snowboard-postgres psql -U snowboard -d snowboard_db
```

#### Полезные команды в psql:

```sql
-- Список таблиц
\dt

-- Структура таблицы
\d videos

-- Просмотр данных
SELECT * FROM videos;

-- Проверка связей
SELECT 
    v.id,
    v.status,
    COUNT(DISTINCT js.id) as stages_count
FROM videos v
LEFT JOIN job_stages js ON js.video_id = v.id
GROUP BY v.id, v.status;
```

### Проверка миграций

```bash
# Текущая версия
cd backend
uv run alembic current

# История миграций
uv run alembic history
```

## Миграции в production

### Основные принципы

1. **Миграции выполняются ДО запуска нового кода**
2. **Миграции выполняются отдельно от приложения**
3. **Всегда делайте бэкап перед миграциями**
4. **Тестируйте на staging перед production**

### Подходы

#### 1. Отдельный Job в CI/CD (рекомендуется)

Миграции выполняются как отдельный шаг в pipeline, приложение запускается только после успешных миграций.

**Пример для GitHub Actions:**

```yaml
jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Run migrations
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          cd backend
          uv run alembic upgrade head
      - name: Verify migration
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          cd backend
          uv run alembic current

  deploy:
    needs: migrate
    # ... деплой приложения
```

#### 2. Init Container (Kubernetes)

```yaml
spec:
  template:
    spec:
      initContainers:
      - name: migrate
        image: snowboard-api:latest
        command: ["uv", "run", "--directory", "backend", "alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
      containers:
      - name: api
        image: snowboard-api:latest
```

#### 3. Отдельный миграционный контейнер (Docker Compose)

```yaml
services:
  migrate:
    build:
      context: ..
      dockerfile: infra/docker/api.Dockerfile
    command: uv run --directory backend alembic upgrade head
    env_file:
      - ../.env
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"  # Выполняется один раз

  api:
    depends_on:
      migrate:
        condition: service_completed_successfully
```

### Workflow для production

```bash
#!/bin/bash
set -e

# 1. Бэкап
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Проверка готовности БД
until pg_isready -h $DB_HOST -U $DB_USER; do
  echo "Waiting for database..."
  sleep 1
done

# 3. Миграции
cd backend
uv run alembic upgrade head

# 4. Проверка
uv run alembic current

# 5. Деплой приложения
```

### Откат миграций

```bash
# Откатить на одну версию назад
alembic downgrade -1

# Откатить на конкретную версию
alembic downgrade <revision>

# Откат через бэкап (если миграции уже применены)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < backup_*.sql
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "UPDATE alembic_version SET version_num='<old_revision>';"
```

## Best Practices

### Обратная совместимость

Миграции должны быть обратно совместимыми:

- ✅ Добавление новых колонок с дефолтными значениями
- ✅ Создание новых таблиц
- ✅ Добавление индексов
- ❌ Удаление колонок (сначала удалите из кода, потом из БД)
- ❌ Изменение типов колонок без дефолтов

**Пример безопасной миграции:**

```python
def upgrade():
    # Добавляем новую колонку с дефолтом
    op.add_column('users', sa.Column('new_field', sa.String(), nullable=True, server_default='default_value'))

def downgrade():
    op.drop_column('users', 'new_field')
```

### Проверка после миграций

```bash
# 1. Версия миграций
alembic current

# 2. Структура БД
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\d"

# 3. Логи приложения
# Убедитесь, что приложение запустилось без ошибок
```

## Troubleshooting

### Ошибка: "Database is not ready"

```bash
# Проверить статус
docker compose -f infra/docker-compose.yml ps

# Посмотреть логи
docker compose -f infra/docker-compose.yml logs postgres
```

### Ошибка: "could not translate host name 'postgres'"

Для локальной разработки команда `make migrate` автоматически заменяет `postgres` на `localhost`. Если ошибка все еще есть:

```bash
# Добавить в /etc/hosts
sudo sh -c 'echo "127.0.0.1 postgres" >> /etc/hosts'
```

### Ошибка: "relation does not exist"

```bash
# Применить миграции
make migrate
```

## Важные замечания

1. **Никогда не применяйте миграции напрямую на production без тестирования на staging**
2. **Всегда делайте бэкап перед миграциями**
3. **Используйте транзакции, когда возможно**
4. **Планируйте откат заранее**
5. **Миграции должны быть идемпотентными** (можно запускать несколько раз без вреда)
