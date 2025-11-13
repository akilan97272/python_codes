from .base import BaseMonitor
import platform, time

try:
    from systemd import journal as systemd_journal
except Exception:
    systemd_journal = None

try:
    import win32evtlog
except Exception:
    win32evtlog = None

IS_WINDOWS = platform.system().lower().startswith("win")
IS_LINUX = platform.system().lower().startswith("linux")

class LogMonitor(BaseMonitor):
    def __init__(self, emitter, windows_channels=None, linux_units=None, poll_interval=1.0):
        super().__init__("log", emitter, poll_interval)
        self.windows_channels = windows_channels or ["Security","System","Application"]
        self.linux_units = linux_units or ["sshd.service","sudo.service"]

    def monitor(self):
        if IS_WINDOWS and win32evtlog is not None:
            self._monitor_windows_eventlog()
        elif IS_LINUX and systemd_journal is not None:
            self._monitor_journald()
        else:
            self.emit("warning", {"msg":"No Log backend available (install pywin32 or python-systemd)"})

    def _monitor_journald(self):
        r = systemd_journal.Reader()
        r.this_boot(); r.seek_tail(); r.get_next()
        for unit in self.linux_units:
            r.add_match(_SYSTEMD_UNIT=unit)
        while not self.stopped():
            if r.wait(int(self.poll_interval * 1e6)):
                for entry in r:
                    self.emit("event", {"unit": entry.get("_SYSTEMD_UNIT"), "msg": entry.get("MESSAGE"), "pid": entry.get("_PID")})
