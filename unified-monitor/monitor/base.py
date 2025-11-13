import threading, time, platform, traceback
from .event import Event
from .emitter import EventEmitter
from typing import Dict, Any

class BaseMonitor(threading.Thread):
    def __init__(self, name: str, emitter: EventEmitter, poll_interval: float = 1.0):
        super().__init__(name=name, daemon=True)
        self.name = name
        self.emitter = emitter
        self.poll_interval = poll_interval
        self._stop_evt = threading.Event()
        self._host = platform.node()
        self._os = platform.platform()

    def stop(self):
        self._stop_evt.set()

    def stopped(self) -> bool:
        return self._stop_evt.is_set()

    def emit(self, subtype: str, data: Dict[str, Any]):
        evt = Event(self.name, subtype, time.time(), self._host, self._os, data)
        self.emitter.emit(evt)

    def run(self):
        try:
            self.monitor()
        except Exception as e:
            self.emit("error", {"error": str(e), "trace": traceback.format_exc()})

    def monitor(self):
        raise NotImplementedError
