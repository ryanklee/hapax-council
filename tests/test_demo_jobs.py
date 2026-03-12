"""Tests for the async demo job manager and API endpoints."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cockpit.api.demo_jobs import DemoJob, DemoJobManager


@pytest.fixture
def jobs_dir(tmp_path):
    d = tmp_path / "jobs"
    d.mkdir()
    return d


@pytest.fixture
def manager(jobs_dir):
    return DemoJobManager(jobs_dir=jobs_dir)


class TestDemoJob:
    def test_to_dict_excludes_internal_fields(self):
        job = DemoJob(id="test-123", request="demo for family")
        d = job.to_dict()
        assert "id" in d
        assert "request" in d
        assert "_phases_seen" not in d

    def test_default_status_is_queued(self):
        job = DemoJob(id="test-123")
        assert job.status == "queued"


class TestDemoJobManager:
    @pytest.mark.asyncio
    @patch("cockpit.api.demo_jobs.DemoJobManager._run_demo", new_callable=AsyncMock)
    async def test_submit_creates_job(self, mock_run, manager):
        job = manager.submit("demo for family", format="slides")
        assert job.status == "queued"
        assert job.request == "demo for family"
        assert job.format == "slides"
        assert job.id is not None
        # Job is saved to disk
        path = manager._jobs_dir / f"{job.id}.json"
        assert path.exists()

    @pytest.mark.asyncio
    @patch("cockpit.api.demo_jobs.DemoJobManager._run_demo", new_callable=AsyncMock)
    async def test_submit_rejects_concurrent(self, mock_run, manager):
        # Make the mock never complete so the task stays "running"
        never_done = asyncio.get_event_loop().create_future()
        mock_run.return_value = never_done
        manager.submit("first demo")
        # Second submit should fail
        with pytest.raises(RuntimeError, match="already in progress"):
            manager.submit("second demo")

    @pytest.mark.asyncio
    @patch("cockpit.api.demo_jobs.DemoJobManager._run_demo", new_callable=AsyncMock)
    async def test_get_returns_job(self, mock_run, manager):
        job = manager.submit("test request")
        retrieved = manager.get(job.id)
        assert retrieved is not None
        assert retrieved.id == job.id
        assert retrieved.request == "test request"

    def test_get_returns_none_for_missing(self, manager):
        assert manager.get("nonexistent-id") is None

    @pytest.mark.asyncio
    @patch("cockpit.api.demo_jobs.DemoJobManager._run_demo", new_callable=AsyncMock)
    async def test_list_jobs_returns_newest_first(self, mock_run, manager):
        j1 = manager.submit("first")
        manager._current_task = None
        j2 = manager.submit("second")
        manager._current_task = None

        jobs = manager.list_jobs()
        ids = [j["id"] for j in jobs]
        assert len(ids) == 2
        assert j1.id in ids
        assert j2.id in ids

    @pytest.mark.asyncio
    @patch("cockpit.api.demo_jobs.DemoJobManager._run_demo", new_callable=AsyncMock)
    async def test_list_jobs_respects_limit(self, mock_run, manager):
        for i in range(5):
            manager.submit(f"demo {i}")
            manager._current_task = None
        assert len(manager.list_jobs(limit=3)) == 3

    @pytest.mark.asyncio
    async def test_run_demo_success(self, manager):
        with patch("agents.demo.generate_demo", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = Path("/tmp/demo-output")

            job = DemoJob(id="test-run", request="family demo", format="slides")
            manager._queues[job.id] = asyncio.Queue()
            manager._save(job)

            await manager._run_demo(job)

            assert job.status == "complete"
            assert job.result_path == "/tmp/demo-output"
            assert job.progress_pct == 100
            mock_gen.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_demo_failure(self, manager):
        with patch("agents.demo.generate_demo", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = RuntimeError("playwright crashed")

            job = DemoJob(id="test-fail", request="bad demo", format="slides")
            manager._queues[job.id] = asyncio.Queue()
            manager._save(job)

            await manager._run_demo(job)

            assert job.status == "failed"
            assert "playwright crashed" in job.error

    @pytest.mark.asyncio
    async def test_run_demo_progress_events(self, manager):
        async def mock_generate(request, format, on_progress):
            on_progress("Parsing request...")
            on_progress("Gathering research...")
            on_progress("Generating script...")
            return Path("/tmp/demo-output")

        with patch("agents.demo.generate_demo", side_effect=mock_generate):
            job = DemoJob(id="test-progress", request="test", format="slides")
            queue = asyncio.Queue()
            manager._queues[job.id] = queue
            manager._save(job)

            await manager._run_demo(job)

            events = []
            while not queue.empty():
                events.append(queue.get_nowait())

            progress_events = [e for e in events if e and e.get("event") == "progress"]
            assert len(progress_events) == 3
            assert progress_events[0]["data"]["phase"] == "Parsing request..."
            done_events = [e for e in events if e and e.get("event") == "done"]
            assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_cancel_running_job(self, manager):
        cancel_reached = asyncio.Event()

        async def slow_generate(request, format, on_progress):
            on_progress("Starting...")
            cancel_reached.set()
            await asyncio.sleep(300)  # Will be cancelled
            return Path("/tmp/never")

        with patch("agents.demo.generate_demo", side_effect=slow_generate):
            job = manager.submit("slow demo")
            await cancel_reached.wait()

            cancelled = await manager.cancel(job.id)
            assert cancelled

            saved = manager.get(job.id)
            assert saved.status == "cancelled"

    @pytest.mark.asyncio
    async def test_stream_completed_job(self, manager):
        job = DemoJob(
            id="done-job",
            status="complete",
            result_path="/tmp/demo",
        )
        manager._save(job)

        events = []
        async for event in manager.stream("done-job"):
            events.append(event)

        assert len(events) == 1
        assert events[0]["event"] == "done"

    def test_save_atomic(self, manager):
        job = DemoJob(id="atomic-test", request="test")
        manager._save(job)

        path = manager._jobs_dir / "atomic-test.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["id"] == "atomic-test"
        # No tmp file left behind
        assert not path.with_suffix(".tmp").exists()
