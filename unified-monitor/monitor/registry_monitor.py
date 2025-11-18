import os
import time
import platform
import socket
from datetime import datetime



# =============================================================
#  SIMPLE EVENT CLASS
# =============================================================
class Event:
    def __init__(self, source, subtype, ts, host, os, data):
        self.source = source
        self.subtype = subtype
        self.ts = ts
        self.host = host
        self.os = os
        self.data = data


# =============================================================
#  CLEAN HUMAN-READABLE EMITTER
# =============================================================
class EventEmitter:
    def emit(self, event: Event):
        timestamp = datetime.fromtimestamp(event.ts).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{event.subtype.upper()}] {timestamp}")
        print(f"File:     {event.data.get('file')}")
        print(f"Message:  {event.data.get('message')}")
        print()  # blank line


# =============================================================
#  EVENT WRAPPER
# =============================================================
def emit_event(emitter, subtype, data):
    event = Event(
        source="registry",
        subtype=subtype,
        ts=datetime.now().timestamp(),
        host=socket.gethostname(),
        os=platform.platform(),
        data=data
    )
    emitter.emit(event)


# =============================================================
#  TRACK FILE CREATION, MODIFICATION, DELETION
# =============================================================
def scan_files(root_paths):
    """
    Returns a dict: { file_path: mtime }
    """
    snapshot = {}

    for root in root_paths:
        if not os.path.isdir(root):
            continue

        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                try:
                    snapshot[full_path] = os.path.getmtime(full_path)
                except Exception:
                    pass

    return snapshot


# =============================================================
#  MAIN LINUX CONFIG MONITOR
# =============================================================
def monitor_linux_config(emitter, paths, interval=1.0):
    print("[registry-monitor] Linux config monitor started")
    print("[registry-monitor] Watching:")
    for p in paths:
        print(" •", p)
    print()

    previous = scan_files(paths)

    while True:
        time.sleep(interval)
        current = scan_files(paths)

        # --- Detect deleted files ---
        for f in previous:
            if f not in current:
                emit_event(emitter, "change", {
                    "file": f,
                    "message": "File deleted"
                })

        # --- Detect newly created files ---
        for f in current:
            if f not in previous:
                emit_event(emitter, "change", {
                    "file": f,
                    "message": "File created"
                })

        # --- Detect modified files ---
        for f in current:
            if f in previous and current[f] != previous[f]:
                emit_event(emitter, "change", {
                    "file": f,
                    "message": "File modified"
                })

        previous = current


# =============================================================
#  WINDOWS REGISTRY MONITOR (DISABLED ON LINUX)
# =============================================================
def monitor_windows_registry(emitter):
    try:
        import wmi
    except:
        emit_event(emitter, "error", {"message": "WMI not installed"})
        return

    emit_event(emitter, "info", {"message": "Windows registry monitoring started"})

    c = wmi.WMI()
    watcher = c.watch_for(
        notification_type='Creation',
        wmi_class='RegistryValueChangeEvent'
    )

    while True:
        try:
            evt = watcher()
            emit_event(emitter, "change", {
                "file": evt.KeyPath,
                "message": f"Registry value changed: {evt.ValueName}"
            })
        except Exception as e:
            emit_event(emitter, "error", {"message": str(e)})
            time.sleep(1)


# =============================================================
#  ENTRY POINT
# =============================================================
if __name__ == "__main__":
    emitter = EventEmitter()

    if platform.system().lower().startswith("win"):
        monitor_windows_registry(emitter)
    else:
        monitor_linux_config(
            emitter,
            paths=[
                "/etc",
                os.path.expanduser("~/.config")
            ],
            interval=1.0
        )
