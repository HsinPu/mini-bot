import asyncio

from opensprite.utils import processes as processes_module


class _FakeKiller:
    def __init__(self):
        self.kill_called = False

    async def wait(self):
        return 0

    def kill(self):
        self.kill_called = True


class _FakeProcess:
    def __init__(self, *, pid: int = 123, wait_delay: float = 0.0):
        self.pid = pid
        self.wait_delay = wait_delay
        self.returncode = None
        self.kill_called = False
        self.wait_calls = 0

    async def wait(self):
        self.wait_calls += 1
        if self.kill_called:
            self.returncode = -9
            return self.returncode
        if self.wait_delay:
            await asyncio.sleep(self.wait_delay)
        self.returncode = 0
        return self.returncode

    def kill(self):
        self.kill_called = True


def test_terminate_process_tree_uses_taskkill_on_windows(monkeypatch):
    taskkill_calls = []

    async def fake_create_subprocess_exec(*args, **kwargs):
        taskkill_calls.append((args, kwargs))
        return _FakeKiller()

    monkeypatch.setattr(processes_module.os, "name", "nt", raising=False)
    monkeypatch.setattr(processes_module.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    process = _FakeProcess(pid=456)

    asyncio.run(processes_module.terminate_process_tree(process, wait_timeout=0.01))

    assert taskkill_calls == [
        (
            ("taskkill", "/PID", "456", "/T", "/F"),
            {
                "stdout": processes_module.asyncio.subprocess.DEVNULL,
                "stderr": processes_module.asyncio.subprocess.DEVNULL,
            },
        )
    ]
    assert process.returncode == 0
    assert process.kill_called is False


def test_terminate_process_tree_falls_back_to_direct_kill_when_wait_times_out(monkeypatch):
    killpg_calls = []

    def fake_killpg(pid, sig):
        killpg_calls.append((pid, sig))

    monkeypatch.setattr(processes_module.os, "name", "posix", raising=False)
    monkeypatch.setattr(processes_module.os, "killpg", fake_killpg, raising=False)
    monkeypatch.setattr(processes_module.signal, "SIGKILL", "SIGKILL", raising=False)

    process = _FakeProcess(pid=789, wait_delay=0.05)

    asyncio.run(processes_module.terminate_process_tree(process, wait_timeout=0.01))

    assert killpg_calls == [(789, processes_module.signal.SIGKILL)]
    assert process.kill_called is True
    assert process.returncode == -9
