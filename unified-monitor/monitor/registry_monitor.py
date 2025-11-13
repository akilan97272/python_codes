from .base import BaseMonitor
import platform

try:
    import wmi
except Exception:
    wmi = None

IS_WINDOWS = platform.system().lower().startswith("win")

class RegistryMonitor(BaseMonitor):
    def __init__(self, emitter, keys=None, poll_interval=2.0):
        super().__init__("registry", emitter, poll_interval)
        self.keys = keys or [r"HKEY_LOCAL_MACHINE\\SOFTWARE", r"HKEY_CURRENT_USER\\SOFTWARE"]

    def monitor(self):
        if not IS_WINDOWS:
            self.emit("info", {"msg":"RegistryMonitor disabled: non-Windows"})
            return
        if wmi is not None:
            self._monitor_wmi_registry()
        else:
            self.emit("warning", {"msg":"No registry backend (pywin32/WMI) available"})

    def _monitor_wmi_registry(self):
        c = wmi.WMI()
        watcher = c.watch_for(notification_type='Creation', wmi_class='RegistryValueChangeEvent')
        while not self.stopped():
            try:
                evt = watcher(timeout_ms=int(self.poll_interval*1000))
                if not evt: continue
                hive = getattr(evt, 'Hive', None)
                key = getattr(evt, 'KeyPath', None)
                value = getattr(evt, 'ValueName', None)
                self.emit("change", {"hive": hive, "key": key, "value": value})
            except Exception as e:
                self.emit("error", {"stage":"wmi_reg","err":str(e)})
                import time; time.sleep(self.poll_interval)
