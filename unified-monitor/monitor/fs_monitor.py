from .base import BaseMonitor
import os, time
from typing import List
try:
    from inotify_simple import INotify, flags
except Exception:
    INotify = None
    flags = None

try:
    from watchdog.observers import Observer as WatchdogObserver
    from watchdog.events import FileSystemEventHandler as WatchdogHandler
except Exception:
    WatchdogObserver = None
    WatchdogHandler = None

class FSMonitor(BaseMonitor):
    def __init__(self, emitter, paths: List[str], enable_integrity: bool = True, poll_interval: float = 1.0):
        super().__init__("fs", emitter, poll_interval)
        self.paths = paths
        self.enable_integrity = enable_integrity

    def monitor(self):
        if INotify is not None:
            self._monitor_inotify()
        elif WatchdogObserver is not None:
            self._monitor_watchdog()
        else:
            self.emit("warning", {"msg":"No FS backend available"})

    def _monitor_inotify(self):
        inotify = INotify()
        watches = {}
        mask = flags.CREATE | flags.MODIFY | flags.DELETE | flags.MOVED_FROM | flags.MOVED_TO
        for p in self.paths:
            try:
                wd = inotify.add_watch(p, mask)
                watches[wd] = p
            except Exception as e:
                self.emit("warning", {"path": p, "err": str(e)})
        while not self.stopped():
            events = inotify.read(timeout=int(self.poll_interval*1000))
            for e in events:
                base = watches.get(e.wd, "?")
                name = e.name.decode("utf-8", errors="ignore") if isinstance(e.name,(bytes,bytearray)) else e.name
                path = os.path.join(base, name) if name else base
                subtype = "modify" if e.mask & flags.MODIFY else "create" if e.mask & flags.CREATE else "delete" if e.mask & flags.DELETE else "move"
                payload = {"path": path}
                self.emit(subtype, payload)

    def _monitor_watchdog(self):
        class Handler(WatchdogHandler):
            def __init__(self, outer):
                self.outer = outer
                super().__init__()
            def on_created(self, event):
                if event.is_directory: return
                self.outer.emit("create", {"path": event.src_path})
            def on_modified(self, event):
                if event.is_directory: return
                self.outer.emit("modify", {"path": event.src_path})
            def on_moved(self, event):
                self.outer.emit("move", {"src": event.src_path, "dst": event.dest_path})
            def on_deleted(self, event):
                self.outer.emit("delete", {"path": event.src_path})
        obs = WatchdogObserver()
        handler = Handler(self)
        for p in self.paths:
            try:
                obs.schedule(handler, p, recursive=True)
            except Exception as e:
                self.emit("warning", {"path": p, "err": str(e)})
        obs.start()
        try:
            while not self.stopped():
                time.sleep(self.poll_interval)
        finally:
            obs.stop(); obs.join()
