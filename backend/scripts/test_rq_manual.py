"""Test script for Redis connection and queue functionality."""

import os
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Fix REDIS_URL for local execution (replace redis hostname with localhost)
# Must be done BEFORE importing any backend modules that load settings
os.environ["REDIS_URL"] = "redis://localhost:6379/0"


from backend.app.adapters.redis import QueueClient
from backend.app.adapters.redis.client import check_redis_health, get_redis_connection


def test_redis_connection() -> bool:
    """Test Redis connection."""
    print("Testing Redis connection...")
    try:
        conn = get_redis_connection()
        result = conn.ping()
        print(f"✓ Redis ping successful: {result}")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False


def test_redis_health() -> bool:
    """Test Redis health check."""
    print("\nTesting Redis health check...")
    try:
        is_healthy = check_redis_health()
        if is_healthy:
            print("✓ Redis health check passed")
        else:
            print("✗ Redis health check failed")
        return is_healthy
    except Exception as e:
        print(f"✗ Redis health check error: {e}")
        return False


def test_enqueue_task() -> bool:
    """Test task enqueueing."""
    print("\nTesting task enqueueing...")
    try:
        queue_client = QueueClient(get_redis_connection())

        # Test enqueue to CPU queue
        test_video_id = uuid4()
        print(f"Enqueueing transcode task for video_id: {test_video_id}")
        job = queue_client.enqueue_transcode_task(test_video_id)
        print(f"✓ Task enqueued to CPU queue. Job ID: {job.id}")

        # Test enqueue to GPU queue
        print(f"Enqueueing pose task for video_id: {test_video_id}")
        job = queue_client.enqueue_pose_task(test_video_id)
        print(f"✓ Task enqueued to GPU queue. Job ID: {job.id}")

        return True
    except Exception as e:
        print(f"✗ Task enqueueing failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main() -> None:
    """Run all tests."""
    print("=" * 60)
    print("Redis and Queue Test")
    print("=" * 60)

    results = []

    results.append(("Redis Connection", test_redis_connection()))
    results.append(("Redis Health Check", test_redis_health()))
    results.append(("Task Enqueueing", test_enqueue_task()))

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")

    all_passed = all(result[1] for result in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
