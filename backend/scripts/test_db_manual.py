"""Интерактивный скрипт для ручного тестирования БД."""

import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Fix DATABASE_URL for local execution (replace postgres with localhost)
# Must be done BEFORE importing settings
if "DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace("@postgres:", "@localhost:")

# ruff: noqa
from sqlalchemy import text

from backend.app.domain.analysis_job import Stage, StageStatus
from backend.app.domain.value_objects import ArtifactKind
from backend.app.infrastructure.postgres.orm_models import (
    Artifact,
    JobStage,
    Video,
    VideoStatus,
)
from backend.app.composition.settings import load_settings
from backend.app.infrastructure.postgres.session import (
    create_engine_from_settings,
    create_sessionmaker_from_engine,
)

settings = load_settings()
engine = create_engine_from_settings(settings)
SessionLocal = create_sessionmaker_from_engine(engine)


def print_separator():
    """Печатает разделитель."""
    print("\n" + "=" * 60 + "\n")


def main():
    """Главная функция."""
    print_separator()
    print("ТЕСТИРОВАНИЕ МОДЕЛЕЙ БД")
    print_separator()
    # Проверяем подключение
    print("\n1. Проверка подключения к БД...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            print(f"✓ Подключение успешно! (результат: {result})")
    except Exception as e:
        print(f"✗ Ошибка подключения: {e}")
        return

    db = SessionLocal()
    try:
        print_separator()
        print("2. Создание тестового видео...")

        # Создаем видео
        video = Video(
            id=uuid.uuid4(),
            status=VideoStatus.CREATED,
            share_token=f"test_token_{uuid.uuid4().hex[:8]}",
            original_filename="test_video.mp4",
            original_size_bytes=1024000,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        print("✓ Видео создано:")
        print(f"  ID: {video.id}")
        print(f"  Статус: {video.status.value}")
        print(f"  Token: {video.share_token}")
        print(f"  Файл: {video.original_filename}")
        print(f"  Размер: {video.original_size_bytes} bytes")
        print(f"  Создано: {video.created_at}")

        print_separator()
        print("3. Создание стадий обработки...")

        # Создаем стадии
        stages = [
            JobStage(
                video_id=video.id,
                name=Stage.TRANSCODE,
                status=StageStatus.PENDING,
            ),
            JobStage(
                video_id=video.id,
                name=Stage.POSE,
                status=StageStatus.PENDING,
            ),
            JobStage(
                video_id=video.id,
                name=Stage.FEATURES,
                status=StageStatus.PENDING,
            ),
            JobStage(
                video_id=video.id,
                name=Stage.FEEDBACK,
                status=StageStatus.PENDING,
            ),
        ]

        for stage in stages:
            db.add(stage)
        db.commit()

        print(f"✓ Создано {len(stages)} стадий:")
        for stage in stages:
            print(f"  - {stage.name.value}: {stage.status.value}")

        print_separator()
        print("4. Создание артефактов...")

        # Создаем артефакты
        artifacts = [
            Artifact(
                video_id=video.id,
                kind=ArtifactKind.ORIGINAL,
                version="v1",
                object_key=f"raw/{video.id}/original.mp4",
            ),
            Artifact(
                video_id=video.id,
                kind=ArtifactKind.NORMALIZED,
                version="v1",
                object_key=f"raw/{video.id}/normalized.mp4",
            ),
        ]

        for artifact in artifacts:
            db.add(artifact)
        db.commit()

        print(f"✓ Создано {len(artifacts)} артефактов:")
        for artifact in artifacts:
            print(f"  - {artifact.kind.value} v{artifact.version}")
            print(f"    Key: {artifact.object_key}")

        print_separator()
        print("5. Проверка связей (relationships)...")

        # Обновляем объект из БД для загрузки связей
        db.refresh(video)

        print(f"✓ Видео имеет {len(video.stages)} стадий")
        print(f"✓ Видео имеет {len(video.artifacts)} артефактов")

        if video.stages:
            print("\n  Стадии:")
            for stage in video.stages:
                print(f"    - {stage.name.value}: {stage.status.value}")

        if video.artifacts:
            print("\n  Артефакты:")
            for artifact in video.artifacts:
                print(f"    - {artifact.kind.value} {artifact.version}")

        print_separator()
        print("6. Тест переходов статусов...")

        # Обновляем статус видео
        video.status = VideoStatus.UPLOADED
        db.commit()
        print(f"✓ Видео: {video.status.value}")

        # Обновляем стадию
        transcode_stage = (
            db.query(JobStage)
            .filter(JobStage.video_id == video.id, JobStage.name == Stage.TRANSCODE)
            .first()
        )

        if transcode_stage:
            transcode_stage.status = StageStatus.RUNNING
            transcode_stage.started_at = datetime.now(UTC)
            db.commit()
            print(f"✓ Стадия {transcode_stage.name.value}: {transcode_stage.status.value}")
            print(f"  Начало: {transcode_stage.started_at}")

            transcode_stage.status = StageStatus.DONE
            transcode_stage.ended_at = datetime.now(UTC)
            video.status = VideoStatus.PROCESSING
            db.commit()
            print(f"✓ Стадия {transcode_stage.name.value}: {transcode_stage.status.value}")
            print(f"  Завершено: {transcode_stage.ended_at}")
            print(f"✓ Видео: {video.status.value}")

        print_separator()
        print("7. Тест запросов...")

        # Подсчет записей
        video_count = db.query(Video).count()
        print(f"✓ Всего видео в БД: {video_count}")

        # Поиск по статусу
        processing_videos = db.query(Video).filter(Video.status == VideoStatus.PROCESSING).all()
        print(f"✓ Видео в обработке: {len(processing_videos)}")

        # Поиск стадий
        running_stages = db.query(JobStage).filter(JobStage.status == StageStatus.RUNNING).all()
        print(f"✓ Запущенных стадий: {len(running_stages)}")

        print_separator()
        print("✓ Все тесты пройдены успешно!")
        print(f"\nВидео ID для дальнейших проверок: {video.id}")
        print(f"Share token: {video.share_token}")

    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
