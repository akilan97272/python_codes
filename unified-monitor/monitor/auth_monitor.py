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

class AuthMonitor(BaseMonitor):
    def __init__(self, emitter, poll_interval=1.0):
        super().__init__("auth", emitter, poll_interval)

    def monitor(self):
        if IS_WINDOWS and win32evtlog is not None:
            self._windows_auth()
        elif IS_LINUX and systemd_journal is not None:
            self._linux_auth_journal()
        else:
            self.emit("warning", {"msg":"No auth backend available"})

    def _linux_auth_journal(self):
        r = systemd_journal.Reader()
        r.this_boot(); r.seek_tail(); r.get_next()
        r.add_match(_SYSTEMD_UNIT="sshd.service")
        while not self.stopped():
            if r.wait(int(self.poll_interval * 1e6)):
                for entry in r:
                    msg = entry.get("MESSAGE") or ""
                    if any(k in msg.lower() for k in ["authentication failure","failed password","accepted password","accepted publickey"]):
                        self.emit("event", {"unit":"sshd.service","msg":msg,"pid":entry.get("_PID")})
