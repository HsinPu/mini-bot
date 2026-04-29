"""Runtime manager for per-session cron services."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Awaitable, Callable

from ..context.paths import get_session_workspace
from .service import CronService
from .types import CronJob


class CronManager:
    """Manage per-session cron services under the workspace root."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        on_job: Callable[[str, CronJob], Awaitable[str | None]],
    ):
        self.workspace_root = Path(workspace_root)
        self._on_job = on_job
        self._services: dict[str, CronService] = {}
        self._lock = asyncio.Lock()

    def _jobs_path(self, session_id: str) -> Path:
        return get_session_workspace(session_id, workspace_root=self.workspace_root) / "cron" / "jobs.json"

    def _iter_jobs_paths(self):
        for root_name in ("sessions", "chats"):
            root = self.workspace_root / root_name
            if not root.exists():
                continue
            yield from root.glob("*/*/cron/jobs.json")

    @staticmethod
    def _session_id_from_jobs_path(jobs_path: Path) -> str:
        try:
            return str(json.loads(jobs_path.read_text(encoding="utf-8")).get("sessionId", "")).strip()
        except Exception:
            return ""

    async def _build_service(self, session_id: str) -> CronService:
        async def on_job(job: CronJob) -> str | None:
            return await self._on_job(session_id, job)

        service = CronService(
            self._jobs_path(session_id),
            session_id=session_id,
            on_job=on_job,
        )
        await service.start()
        return service

    async def get_or_create_service(self, session_id: str) -> CronService:
        async with self._lock:
            service = self._services.get(session_id)
            if service is not None:
                return service
            service = await self._build_service(session_id)
            self._services[session_id] = service
            return service

    async def get_all_services(self) -> dict[str, CronService]:
        """Return services for every discovered session with a cron store."""
        session_ids = {
            session_id
            for jobs_path in self._iter_jobs_paths()
            if (session_id := self._session_id_from_jobs_path(jobs_path))
        }
        for session_id in sorted(session_ids):
            await self.get_or_create_service(session_id)
        async with self._lock:
            return dict(self._services)

    async def start(self) -> None:
        for jobs_path in self._iter_jobs_paths():
            session_id = self._session_id_from_jobs_path(jobs_path)
            if not session_id:
                continue
            await self.get_or_create_service(session_id)

    async def stop(self) -> None:
        async with self._lock:
            services = list(self._services.values())
            self._services.clear()
        for service in services:
            service.stop()


__all__ = ["CronManager"]
