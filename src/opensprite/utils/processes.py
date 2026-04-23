"""Process lifecycle helpers shared across the codebase."""

import asyncio
import contextlib
import os
import signal


_WINDOWS_FORCE_FOLLOWUP_DELAY = 0.25


async def _run_taskkill(pid: int, *, force: bool, wait_timeout: float) -> None:
    """Best-effort invoke taskkill for a Windows process tree."""
    args = ["taskkill", "/PID", str(pid), "/T"]
    if force:
        args.append("/F")

    try:
        killer = await asyncio.create_subprocess_exec(
            *args,
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


async def _wait_for_process_exit(process: asyncio.subprocess.Process, *, wait_timeout: float) -> bool:
    """Wait for a process to exit, returning False on timeout."""
    if process.returncode is not None:
        return True

    try:
        await asyncio.wait_for(process.wait(), timeout=wait_timeout)
        return True
    except asyncio.TimeoutError:
        return process.returncode is not None


def _signal_unix_process_tree(process: asyncio.subprocess.Process, sig: int) -> None:
    """Send a Unix signal to the process group, falling back to the direct process."""
    try:
        os.killpg(process.pid, sig)
        return
    except ProcessLookupError:
        return
    except Exception:
        pass

    try:
        if sig == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
    except ProcessLookupError:
        return
    except Exception:
        return


async def terminate_process_tree(
    process: asyncio.subprocess.Process,
    *,
    wait_timeout: float = 5,
) -> None:
    """Best-effort terminate a process and its descendants."""
    if process.returncode is not None:
        return

    if os.name == "nt":
        await _run_taskkill(process.pid, force=False, wait_timeout=wait_timeout)
        # cmd.exe can exit before its descendants are fully gone, so keep the
        # grace window short and follow with a forced tree kill for reliability.
        settle_timeout = min(wait_timeout, _WINDOWS_FORCE_FOLLOWUP_DELAY)
        if settle_timeout > 0:
            await _wait_for_process_exit(process, wait_timeout=settle_timeout)

        await _run_taskkill(process.pid, force=True, wait_timeout=wait_timeout)
        if await _wait_for_process_exit(process, wait_timeout=wait_timeout):
            return

        with contextlib.suppress(ProcessLookupError):
            process.kill()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(process.wait(), timeout=wait_timeout)
        return

    _signal_unix_process_tree(process, signal.SIGTERM)

    if await _wait_for_process_exit(process, wait_timeout=wait_timeout):
        return

    _signal_unix_process_tree(process, signal.SIGKILL)

    if await _wait_for_process_exit(process, wait_timeout=wait_timeout):
        return

    with contextlib.suppress(ProcessLookupError):
        process.kill()
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(process.wait(), timeout=wait_timeout)
