"""Process lifecycle helpers shared across the codebase."""

import asyncio
import contextlib
import os
import signal


async def _terminate_windows_process_tree(pid: int, *, wait_timeout: float) -> None:
    """Best-effort terminate a Windows process tree via taskkill."""
    try:
        killer = await asyncio.create_subprocess_exec(
            "taskkill",
            "/PID",
            str(pid),
            "/T",
            "/F",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except Exception:
        return

    try:
        await asyncio.wait_for(killer.wait(), timeout=wait_timeout)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            killer.kill()
        with contextlib.suppress(Exception):
            await killer.wait()


async def terminate_process_tree(
    process: asyncio.subprocess.Process,
    *,
    wait_timeout: float = 5,
) -> None:
    """Best-effort terminate a process and its descendants."""
    if process.returncode is not None:
        return

    if os.name == "nt":
        await _terminate_windows_process_tree(process.pid, wait_timeout=wait_timeout)
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)

    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(process.wait(), timeout=wait_timeout)

    if process.returncode is None:
        with contextlib.suppress(ProcessLookupError):
            process.kill()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(process.wait(), timeout=wait_timeout)
