"""
Batch agent persona generation service.
Handles generating personas for 1000+ agents with rate limiting,
progress tracking, and efficient queue management.
"""

import asyncio
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from app.services.llm_persona_generator import (
    generate_and_save_persona,
    reset_corpus_cache,
)
import logging

logger = logging.getLogger(__name__)


@dataclass
class GenerationJob:
    """Represents a single persona generation job."""

    agent_id: str
    agent_metadata: Dict[str, Any]
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class BatchPersonaGenerator:
    """Manages batch generation of agent personas."""

    def __init__(self, max_concurrent: int = 3, rate_limit_delay: float = 0.5):
        """
        Initialize batch generator.

        Args:
            max_concurrent: Max concurrent LLM calls (default 3 to avoid overwhelming Ollama)
            rate_limit_delay: Delay between LLM calls in seconds
        """
        self.max_concurrent = max_concurrent
        self.rate_limit_delay = rate_limit_delay
        self.jobs: Dict[str, GenerationJob] = {}
        self.queue: asyncio.Queue = None
        self.worker_tasks: List[asyncio.Task] = []

    async def add_job(
        self, agent_id: str, agent_metadata: Dict[str, Any]
    ) -> GenerationJob:
        """Add a generation job to the queue."""
        job = GenerationJob(agent_id, agent_metadata)
        self.jobs[agent_id] = job

        if self.queue:
            await self.queue.put(job)

        return job

    async def add_batch(self, agents: List[Dict[str, Any]]) -> List[GenerationJob]:
        """
        Add multiple agents for persona generation.

        Args:
            agents: List of agent metadata dicts (must include 'id' and name fields)

        Returns:
            List of GenerationJob objects
        """
        jobs = []
        for agent_meta in agents:
            agent_id = (
                agent_meta.get("id")
                or f"agent_{agent_meta.get('name', 'unknown').lower()}"
            )
            job = await self.add_job(agent_id, agent_meta)
            jobs.append(job)

        return jobs

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes jobs from queue."""
        logger.info(f"Worker {worker_id} started")

        while True:
            try:
                # Get job with timeout (to allow graceful shutdown)
                job = await asyncio.wait_for(self.queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                # No jobs for 5 seconds; check if we should stop
                if self.queue.empty():
                    break
                continue

            if job is None:  # Sentinel value for shutdown
                break

            await self._process_job(job, worker_id)
            self.queue.task_done()

            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)

        logger.info(f"Worker {worker_id} stopped")

    async def _process_job(self, job: GenerationJob, worker_id: int) -> None:
        """Process a single generation job."""
        job.status = "in_progress"
        job.started_at = datetime.now()

        logger.info(
            f"[Worker {worker_id}] Processing {job.agent_id} ({job.agent_metadata.get('name')})"
        )

        try:
            # Shift blocking LLM call to a separate thread for true concurrency
            result = await asyncio.to_thread(
                generate_and_save_persona, job.agent_metadata, job.agent_id
            )
            job.result = result
            job.status = "completed"
            job.completed_at = datetime.now()
            elapsed = (job.completed_at - job.started_at).total_seconds()
            logger.info(
                f"[Worker {worker_id}] Completed {job.agent_id} in {elapsed:.1f}s"
            )

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.now()
            logger.error(f"[Worker {worker_id}] Failed {job.agent_id}: {e}")

    async def start(self) -> None:
        """Start worker pool."""
        self.queue = asyncio.Queue()
        self.worker_tasks = []

        for i in range(self.max_concurrent):
            task = asyncio.create_task(self._worker(i))
            self.worker_tasks.append(task)

        logger.info(f"Batch generator started with {self.max_concurrent} workers")

    async def stop(self) -> None:
        """Stop worker pool and wait for pending jobs."""
        if not self.queue:
            return

        # Wait for queue to be empty
        await self.queue.join()

        # Send sentinel values to stop workers
        for _ in range(self.max_concurrent):
            await self.queue.put(None)

        # Wait for workers to finish
        await asyncio.gather(*self.worker_tasks)
        logger.info("Batch generator stopped")

    def get_job_status(self, agent_id: str) -> Optional[GenerationJob]:
        """Get status of a specific job."""
        return self.jobs.get(agent_id)

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all jobs."""
        return {
            agent_id: {
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat()
                if job.completed_at
                else None,
                "error": job.error,
                "sections": list(job.result.keys()) if job.result else [],
            }
            for agent_id, job in self.jobs.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        total = len(self.jobs)
        completed = sum(1 for j in self.jobs.values() if j.status == "completed")
        failed = sum(1 for j in self.jobs.values() if j.status == "failed")
        pending = sum(1 for j in self.jobs.values() if j.status == "pending")
        in_progress = sum(1 for j in self.jobs.values() if j.status == "in_progress")

        elapsed_times = [
            (j.completed_at - j.started_at).total_seconds()
            for j in self.jobs.values()
            if j.completed_at and j.started_at
        ]
        avg_time = (
            sum(elapsed_times) / len(elapsed_times) if elapsed_times else 30.0
        )  # Fallback to 30s

        # Agents currently being processed
        current_agents = [
            job.agent_metadata.get("name", job.agent_id)
            for job in self.jobs.values()
            if job.status == "in_progress"
        ]

        # Last 5 successfully completed agent names
        recently_completed = [
            job.agent_metadata.get("name", job.agent_id)
            for job in sorted(
                (
                    j
                    for j in self.jobs.values()
                    if j.status == "completed" and j.completed_at
                ),
                key=lambda j: j.completed_at,
                reverse=True,
            )[:5]
        ]

        # Last 3 failed agent names with their errors
        recently_failed = [
            {
                "name": job.agent_metadata.get("name", job.agent_id),
                "error": job.error or "unknown",
            }
            for job in sorted(
                (
                    j
                    for j in self.jobs.values()
                    if j.status == "failed" and j.completed_at
                ),
                key=lambda j: j.completed_at,
                reverse=True,
            )[:3]
        ]

        # Overall elapsed seconds since first job was created
        all_created = [j.created_at for j in self.jobs.values() if j.created_at]
        elapsed_since_start = 0.0
        if all_created:
            earliest = min(all_created)
            elapsed_since_start = (datetime.now() - earliest).total_seconds()

        # Calculate wall clock remaining: how many rounds of parallel processing are left
        rounds = (
            math.ceil((pending + in_progress) / self.max_concurrent)
            if self.max_concurrent > 0
            else 0
        )
        est_remaining = rounds * avg_time

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "in_progress": in_progress,
            "completion_percent": (completed / total * 100) if total > 0 else 0,
            "avg_time_per_agent": round(avg_time, 2),
            "estimated_time_remaining": round(est_remaining, 1),
            "elapsed_seconds": round(elapsed_since_start, 1),
            "current_agents": current_agents,
            "recently_completed": recently_completed,
            "recently_failed": recently_failed,
            "workers": self.max_concurrent,
        }


# Global batch generator instance (singleton)
_batch_generator: Optional[BatchPersonaGenerator] = None


def get_batch_generator(max_concurrent: int = 20) -> BatchPersonaGenerator:
    """Get or create the global batch generator instance."""
    global _batch_generator
    if _batch_generator is None:
        _batch_generator = BatchPersonaGenerator(max_concurrent=max_concurrent)
    return _batch_generator


def reset_batch_generator(max_concurrent: int = 20) -> BatchPersonaGenerator:
    """
    Reset the global batch generator (for a fresh batch run).
    Call this before starting a new batch so old job data is cleared.
    """
    global _batch_generator
    reset_corpus_cache()
    _batch_generator = BatchPersonaGenerator(max_concurrent=max_concurrent)
    return _batch_generator


async def generate_personas_batch(
    agents: List[Dict[str, Any]],
    max_concurrent: int = 20,
) -> Dict[str, Any]:
    """
    Generate personas for multiple agents concurrently using the singleton.

    Args:
        agents: List of agent metadata dicts
        max_concurrent: Max concurrent LLM calls

    Returns:
        Generation statistics
    """
    generator = reset_batch_generator(max_concurrent=max_concurrent)

    # Start workers
    await generator.start()

    # Add jobs
    jobs = await generator.add_batch(agents)
    logger.info(f"Added {len(jobs)} jobs to queue")

    # Wait for completion
    await generator.stop()

    return generator.get_stats()
