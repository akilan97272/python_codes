from .base import BaseMonitor
import time
try:
    import psutil
except Exception:
    psutil = None

class ModuleMonitor(BaseMonitor):
    def __init__(self, emitter, poll_interval=5.0):
        super().__init__("module", emitter, poll_interval)
        self._snapshot = {}

    def monitor(self):
        if psutil is None:
            self.emit("warning", {"msg":"psutil not available for module snapshotting"})
            return
        while not self.stopped():
            try:
                for p in psutil.process_iter(attrs=["pid","name"]):
                    pid = p.info["pid"]
                    mods = set()
                    try:
                        for m in p.memory_maps():
                            path = getattr(m,"path",None)
                            if path and (path.endswith(".dll") or path.endswith(".so")):
                                mods.add(path)
                    except Exception:
                        continue
                    old = self._snapshot.get(pid, set())
                    new_add = mods - old
                    removed = old - mods
                    for m in new_add:
                        self.emit("load", {"pid": pid, "module": m, "proc": p.info.get("name")})
                    for m in removed:
                        self.emit("unload", {"pid": pid, "module": m, "proc": p.info.get("name")})
                    self._snapshot[pid] = mods
                dead = [pid for pid in list(self._snapshot.keys()) if not psutil.pid_exists(pid)]
                for pid in dead:
                    self._snapshot.pop(pid, None)
                time.sleep(self.poll_interval)
            except Exception as e:
                self.emit("error", {"stage":"module_poll","err":str(e)})
                time.sleep(self.poll_interval)
