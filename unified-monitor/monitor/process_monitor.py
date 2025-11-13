from typing import Optional, Callable, Dict
import time
from .base import BaseMonitor
import platform

try:
    import psutil
except Exception:
    psutil = None

IS_LINUX = platform.system().lower().startswith("linux")

# BPF stub not included in simple module; will fallback to psutil
class ProcessMonitor(BaseMonitor):
    def __init__(self, emitter, prefer_evented: bool = True, poll_interval: float = 1.0):
        super().__init__("process", emitter, poll_interval)
        self.prefer_evented = prefer_evented
        self.last_seen: Dict[int, float] = {}
        self._impl: Optional[Callable[[], None]] = None
        if psutil is not None:
            self._impl = self._monitor_psutil_poll
            self.emit("info", {"msg": "ProcessMonitor using psutil polling"})
        else:
            self.emit("warning", {"msg": "No provider available for ProcessMonitor"})

    def monitor(self):
        if self._impl:
            self._impl()

    def _monitor_psutil_poll(self):
        if psutil is None:
            return
        while not self.stopped():
            try:
                current = {p.pid: p for p in psutil.process_iter(attrs=["name", "ppid", "cmdline"])}
                for pid, proc in current.items():
                    if pid not in self.last_seen:
                        info = proc.info
                        self.emit("start", {"pid": pid, "name": info.get("name"), "ppid": info.get("ppid"), "cmdline": info.get("cmdline")})
                for pid in list(self.last_seen.keys()):
                    if pid not in current:
                        self.emit("stop", {"pid": pid})
                        self.last_seen.pop(pid, None)
                self.last_seen = {pid: time.time() for pid in current}
                time.sleep(self.poll_interval)
            except Exception as e:
                self.emit("error", {"stage": "psutil", "err": str(e)})
                time.sleep(self.poll_interval)
