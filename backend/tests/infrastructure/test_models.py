"""Tests for database models."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.domain.analysis_job import Stage, StageStatus
from backend.app.domain.value_objects import ArtifactKind, VideoStatus
from backend.app.infrastructure.db.orm_models import (
    ArtifactDB,
    JobStageDB,
    VideoDB,
)
from backend.app.infrastructure.db.session import Base


@pytest.fixture
def test_engine():
    """Create a test database engine."""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session(test_engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_video(test_session: Session) -> VideoDB:
    """Create a sample video for testing."""
    video = VideoDB(
        id=uuid.uuid4(),
        status=VideoStatus.CREATED,
        share_token="test_token_123",
        original_filename="test_video.mp4",
        original_size_bytes=1024000,
    )
    test_session.add(video)
    test_session.commit()
    test_session.refresh(video)
    return video


class TestVideo:
    """Tests for Video model."""

    def test_create_video(self, test_session: Session):
        """Test creating a video."""
        video = VideoDB(
            id=uuid.uuid4(),
            status=VideoStatus.CREATED,
            share_token="unique_token_1",
            original_filename="video.mp4",
            original_size_bytes=5000000,
        )
        test_session.add(video)
        test_session.commit()

        assert video.id is not None
        assert video.status == VideoStatus.CREATED
        assert video.share_token == "unique_token_1"
        assert video.original_filename == "video.mp4"
        assert video.original_size_bytes == 5000000
        assert video.created_at is not None
        assert video.updated_at is not None

    def test_video_unique_share_token(self, test_session: Session, sample_video: VideoDB):
        """Test that share_token must be unique."""
        duplicate_video = VideoDB(
            id=uuid.uuid4(),
            status=VideoStatus.CREATED,
            share_token=sample_video.share_token,  # Same token
            original_filename="another_video.mp4",
        )
        test_session.add(duplicate_video)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_video_status_transitions(self, test_session: Session):
        """Test video status transitions."""
        video = VideoDB(
            id=uuid.uuid4(),
            status=VideoStatus.CREATED,
            share_token="status_test_token",
        )
        test_session.add(video)
        test_session.commit()

        # Test status updates
        video.status = VideoStatus.UPLOADED
        test_session.commit()
        assert video.status == VideoStatus.UPLOADED

        video.status = VideoStatus.PROCESSING
        test_session.commit()
        assert video.status == VideoStatus.PROCESSING

        video.status = VideoStatus.DONE
        test_session.commit()
        assert video.status == VideoStatus.DONE

    def test_video_optional_fields(self, test_session: Session):
        """Test that optional fields can be None."""
        video = VideoDB(
            id=uuid.uuid4(),
            status=VideoStatus.CREATED,
            share_token="optional_test_token",
            original_filename=None,
            original_size_bytes=None,
        )
        test_session.add(video)
        test_session.commit()

        assert video.original_filename is None
        assert video.original_size_bytes is None

    def test_video_relationships(self, test_session: Session, sample_video: VideoDB):
        """Test video relationships with stages and artifacts."""
        # Create a stage
        stage = JobStageDB(
            video_id=sample_video.id,
            name=Stage.TRANSCODE,
            status=StageStatus.PENDING,
        )
        test_session.add(stage)

        # Create an artifact
        artifact = ArtifactDB(
            video_id=sample_video.id,
            kind=ArtifactKind.ORIGINAL,
            version="v1",
            storage_path="raw/test/original.mp4",
        )
        test_session.add(artifact)
        test_session.commit()

        # Test relationships
        assert len(sample_video.stages) == 1
        assert sample_video.stages[0].name == Stage.TRANSCODE
        assert len(sample_video.artifacts) == 1
        assert sample_video.artifacts[0].kind == ArtifactKind.ORIGINAL


class TestJobStage:
    """Tests for JobStage model."""

    def test_create_job_stage(self, test_session: Session, sample_video: VideoDB):
        """Test creating a job stage."""
        stage = JobStageDB(
            video_id=sample_video.id,
            name=Stage.TRANSCODE,
            status=StageStatus.PENDING,
        )
        test_session.add(stage)
        test_session.commit()

        assert stage.id is not None
        assert stage.video_id == sample_video.id
        assert stage.name == Stage.TRANSCODE
        assert stage.status == StageStatus.PENDING
        assert stage.started_at is None
        assert stage.ended_at is None
        assert stage.error_message is None
        assert stage.created_at is not None
        assert stage.updated_at is not None

    def test_job_stage_unique_constraint(self, test_session: Session, sample_video: VideoDB):
        """Test that (video_id, name) must be unique."""
        stage1 = JobStageDB(
            video_id=sample_video.id,
            name=Stage.TRANSCODE,
            status=StageStatus.PENDING,
        )
        test_session.add(stage1)
        test_session.commit()

        # Try to create duplicate
        stage2 = JobStageDB(
            video_id=sample_video.id,
            name=Stage.TRANSCODE,  # Same name
            status=StageStatus.QUEUED,
        )
        test_session.add(stage2)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_job_stage_status_transitions(self, test_session: Session, sample_video: VideoDB):
        """Test job stage status transitions."""
        stage = JobStageDB(
            video_id=sample_video.id,
            name=Stage.POSE,
            status=StageStatus.PENDING,
        )
        test_session.add(stage)
        test_session.commit()

        # Test status updates with timestamps
        stage.status = StageStatus.QUEUED
        test_session.commit()
        assert stage.status == StageStatus.QUEUED

        stage.status = StageStatus.RUNNING
        stage.started_at = datetime.now(UTC)
        test_session.commit()
        assert stage.status == StageStatus.RUNNING
        assert stage.started_at is not None

        stage.status = StageStatus.DONE
        stage.ended_at = datetime.now(UTC)
        test_session.commit()
        assert stage.status == StageStatus.DONE
        assert stage.ended_at is not None

    def test_job_stage_versioning_fields(self, test_session: Session, sample_video: VideoDB):
        """Test optional versioning fields."""
        stage = JobStageDB(
            video_id=sample_video.id,
            name=Stage.POSE,
            status=StageStatus.PENDING,
            pipeline_version="mvp_v1",
            model_version="v1",
        )
        test_session.add(stage)
        test_session.commit()

        assert stage.pipeline_version == "mvp_v1"
        assert stage.model_version == "v1"

    def test_job_stage_error_message(self, test_session: Session, sample_video: VideoDB):
        """Test error message for failed stages."""
        stage = JobStageDB(
            video_id=sample_video.id,
            name=Stage.FEATURES,
            status=StageStatus.FAILED,
            error_message="Processing failed: out of memory",
        )
        test_session.add(stage)
        test_session.commit()

        assert stage.status == StageStatus.FAILED
        assert stage.error_message == "Processing failed: out of memory"

    def test_job_stage_cascade_delete(self, test_session: Session):
        """Test that stages are deleted when video is deleted."""
        video = VideoDB(
            id=uuid.uuid4(),
            status=VideoStatus.CREATED,
            share_token="cascade_test_token",
        )
        test_session.add(video)
        test_session.commit()

        stage = JobStageDB(
            video_id=video.id,
            name=Stage.TRANSCODE,
            status=StageStatus.PENDING,
        )
        test_session.add(stage)
        test_session.commit()

        stage_id = stage.id

        # Delete video
        test_session.delete(video)
        test_session.commit()

        # Stage should be deleted
        deleted_stage = test_session.get(JobStageDB, stage_id)
        assert deleted_stage is None


class TestArtifact:
    """Tests for Artifact model."""

    def test_create_artifact(self, test_session: Session, sample_video: VideoDB):
        """Test creating an artifact."""
        artifact = ArtifactDB(
            video_id=sample_video.id,
            kind=ArtifactKind.NORMALIZED,
            version="v1",
            storage_path="raw/test/normalized.mp4",
        )
        test_session.add(artifact)
        test_session.commit()

        assert artifact.id is not None
        assert artifact.video_id == sample_video.id
        assert artifact.kind == ArtifactKind.NORMALIZED
        assert artifact.version == "v1"
        assert artifact.storage_path == "raw/test/normalized.mp4"
        assert artifact.created_at is not None

    def test_artifact_unique_constraint(self, test_session: Session, sample_video: VideoDB):
        """Test that (video_id, kind, version) must be unique."""
        artifact1 = ArtifactDB(
            video_id=sample_video.id,
            kind=ArtifactKind.KEYPOINTS,
            version="v1",
            storage_path="raw/test/keypoints_v1.jsonl",
        )
        test_session.add(artifact1)
        test_session.commit()

        # Try to create duplicate
        artifact2 = ArtifactDB(
            video_id=sample_video.id,
            kind=ArtifactKind.KEYPOINTS,  # Same kind
            version="v1",  # Same version
            storage_path="raw/test/keypoints_v1_duplicate.jsonl",
        )
        test_session.add(artifact2)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_artifact_different_versions(self, test_session: Session, sample_video: VideoDB):
        """Test that same kind with different versions is allowed."""
        artifact_v1 = ArtifactDB(
            video_id=sample_video.id,
            kind=ArtifactKind.FEATURES,
            version="v1",
            storage_path="raw/test/features_v1.json",
        )
        artifact_v2 = ArtifactDB(
            video_id=sample_video.id,
            kind=ArtifactKind.FEATURES,
            version="v2",  # Different version
            storage_path="raw/test/features_v2.json",
        )
        test_session.add(artifact_v1)
        test_session.add(artifact_v2)
        test_session.commit()

        assert artifact_v1.id != artifact_v2.id
        assert artifact_v1.version == "v1"
        assert artifact_v2.version == "v2"

    def test_artifact_all_kinds(self, test_session: Session, sample_video: VideoDB):
        """Test creating artifacts of all kinds."""
        kinds = [
            ArtifactKind.ORIGINAL,
            ArtifactKind.NORMALIZED,
            ArtifactKind.KEYPOINTS,
            ArtifactKind.FEATURES,
            ArtifactKind.FEEDBACK,
        ]

        for kind in kinds:
            artifact = ArtifactDB(
                video_id=sample_video.id,
                kind=kind,
                version="v1",
                storage_path=f"raw/test/{kind.value}_v1",
            )
            test_session.add(artifact)

        test_session.commit()

        assert len(sample_video.artifacts) == len(kinds)

    def test_artifact_cascade_delete(self, test_session: Session):
        """Test that artifacts are deleted when video is deleted."""
        video = VideoDB(
            id=uuid.uuid4(),
            status=VideoStatus.CREATED,
            share_token="artifact_cascade_test_token",
        )
        test_session.add(video)
        test_session.commit()

        artifact = ArtifactDB(
            video_id=video.id,
            kind=ArtifactKind.ORIGINAL,
            version="v1",
            storage_path="raw/test/original.mp4",
        )
        test_session.add(artifact)
        test_session.commit()

        artifact_id = artifact.id

        # Delete video
        test_session.delete(video)
        test_session.commit()

        # Artifact should be deleted
        deleted_artifact = test_session.get(ArtifactDB, artifact_id)
        assert deleted_artifact is None


class TestModelRelationships:
    """Tests for model relationships."""

    def test_video_with_multiple_stages(self, test_session: Session):
        """Test video with multiple stages."""
        video = VideoDB(
            id=uuid.uuid4(),
            status=VideoStatus.PROCESSING,
            share_token="multi_stage_token",
        )
        test_session.add(video)
        test_session.commit()

        stages = [
            JobStageDB(
                video_id=video.id,
                name=Stage.TRANSCODE,
                status=StageStatus.DONE,
            ),
            JobStageDB(
                video_id=video.id,
                name=Stage.POSE,
                status=StageStatus.RUNNING,
            ),
            JobStageDB(
                video_id=video.id,
                name=Stage.FEATURES,
                status=StageStatus.PENDING,
            ),
            JobStageDB(
                video_id=video.id,
                name=Stage.FEEDBACK,
                status=StageStatus.PENDING,
            ),
        ]

        for stage in stages:
            test_session.add(stage)

        test_session.commit()

        assert len(video.stages) == 4
        assert {stage.name for stage in video.stages} == {
            Stage.TRANSCODE,
            Stage.POSE,
            Stage.FEATURES,
            Stage.FEEDBACK,
        }

    def test_video_with_multiple_artifacts(self, test_session: Session):
        """Test video with multiple artifacts."""
        video = VideoDB(
            id=uuid.uuid4(),
            status=VideoStatus.DONE,
            share_token="multi_artifact_token",
        )
        test_session.add(video)
        test_session.commit()

        artifacts = [
            ArtifactDB(
                video_id=video.id,
                kind=ArtifactKind.ORIGINAL,
                version="v1",
                storage_path="raw/test/original.mp4",
            ),
            ArtifactDB(
                video_id=video.id,
                kind=ArtifactKind.NORMALIZED,
                version="v1",
                storage_path="raw/test/normalized.mp4",
            ),
            ArtifactDB(
                video_id=video.id,
                kind=ArtifactKind.KEYPOINTS,
                version="v1",
                storage_path="raw/test/keypoints_v1.jsonl",
            ),
            ArtifactDB(
                video_id=video.id,
                kind=ArtifactKind.FEATURES,
                version="v1",
                storage_path="raw/test/features_v1.json",
            ),
            ArtifactDB(
                video_id=video.id,
                kind=ArtifactKind.FEEDBACK,
                version="v1",
                storage_path="raw/test/feedback_v1.json",
            ),
        ]

        for artifact in artifacts:
            test_session.add(artifact)

        test_session.commit()

        assert len(video.artifacts) == 5
        assert {artifact.kind for artifact in video.artifacts} == {
            ArtifactKind.ORIGINAL,
            ArtifactKind.NORMALIZED,
            ArtifactKind.KEYPOINTS,
            ArtifactKind.FEATURES,
            ArtifactKind.FEEDBACK,
        }

    def test_complete_video_processing_flow(self, test_session: Session):
        """Test a complete video processing flow with all models."""
        # Create video
        video = VideoDB(
            id=uuid.uuid4(),
            status=VideoStatus.CREATED,
            share_token="complete_flow_token",
            original_filename="snowboard_ride.mp4",
            original_size_bytes=50000000,
        )
        test_session.add(video)
        test_session.commit()

        # Create original artifact
        original_artifact = ArtifactDB(
            video_id=video.id,
            kind=ArtifactKind.ORIGINAL,
            version="v1",
            storage_path="raw/test/original.mp4",
        )
        test_session.add(original_artifact)

        # Update video status
        video.status = VideoStatus.UPLOADED
        test_session.commit()

        # Create transcode stage
        transcode_stage = JobStageDB(
            video_id=video.id,
            name=Stage.TRANSCODE,
            status=StageStatus.QUEUED,
        )
        test_session.add(transcode_stage)

        # Update video status
        video.status = VideoStatus.PROCESSING
        test_session.commit()

        # Simulate transcode completion
        transcode_stage.status = StageStatus.RUNNING
        transcode_stage.started_at = datetime.now(UTC)
        test_session.commit()

        normalized_artifact = ArtifactDB(
            video_id=video.id,
            kind=ArtifactKind.NORMALIZED,
            version="v1",
            storage_path="raw/test/normalized.mp4",
        )
        test_session.add(normalized_artifact)

        transcode_stage.status = StageStatus.DONE
        transcode_stage.ended_at = datetime.now(UTC)
        test_session.commit()

        # Verify relationships
        assert len(video.stages) == 1
        assert len(video.artifacts) == 2
        assert video.status == VideoStatus.PROCESSING
        assert transcode_stage.status == StageStatus.DONE
