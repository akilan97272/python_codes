import os
import time
import socket
import platform
from datetime import datetime


# =============================================================
#  EVENT STRUCTURE
# =============================================================
class Event:
    def __init__(self, source, subtype, ts, host, os, data):
        self.source = source
        self.subtype = subtype      # load, unload, error
        self.ts = ts
        self.host = host
        self.os = os
        self.data = data


# =============================================================
#  HUMAN-READABLE EMITTER
# =============================================================
class EventEmitter:
    def emit(self, event: Event):
        ts = datetime.fromtimestamp(event.ts).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{event.subtype.upper()}] {ts}")
        print(f"Process:  {event.data.get('proc')} (PID: {event.data.get('pid')})")
        print(f"Module:   {event.data.get('module')}")
        print(f"Message:  {event.data.get('message')}")
        print()


# =============================================================
#  EVENT WRAPPER
# =============================================================
def emit_event(emitter, subtype, pid, proc, module, message):
    event = Event(
        source="module",
        subtype=subtype,
        ts=time.time(),
        host=socket.gethostname(),
        os=platform.platform(),
        data={
            "pid": pid,
            "proc": proc,
            "module": module,
            "message": message
        }
    )
    emitter.emit(event)


# =============================================================
#  GET PROCESS NAME
# =============================================================
def get_process_name(pid):
    try:
        with open(f"/proc/{pid}/comm", "r") as f:
            return f.read().strip()
    except:
        return "unknown"


# =============================================================
#  GET LIST OF LOADED MODULES (.so files)
# =============================================================
def get_loaded_modules(pid):
    modules = set()
    maps_file = f"/proc/{pid}/maps"

    if not os.path.exists(maps_file):
        return modules

    try:
        with open(maps_file, "r", errors="ignore") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 6:
                    path = parts[-1]
                    if path.endswith(".so"):  # Linux library
                        modules.add(path)
    except:
        pass

    return modules


# =============================================================
#  MAIN MODULE MONITOR
# =============================================================
def monitor_modules(emitter, interval=2.0):
    print("[module-monitor] Linux module monitor started...\n")

    snapshot = {}  # pid → modules

    while True:
        try:
            # Get list of active PIDs
            pids = [pid for pid in os.listdir("/proc") if pid.isdigit()]

            for pid in pids:
                pid = int(pid)
                proc_name = get_process_name(pid)

                new_modules = get_loaded_modules(pid)
                old_modules = snapshot.get(pid, set())

                # -------- Detect New Modules Loaded --------
                for mod in new_modules - old_modules:
                    emit_event(emitter, "load", pid, proc_name, mod, "Module loaded")

                # -------- Detect Modules Unloaded --------
                for mod in old_modules - new_modules:
                    emit_event(emitter, "unload", pid, proc_name, mod, "Module unloaded")

                # FIX: correct snapshot update
                snapshot[pid] = new_modules

            # Remove processes that no longer exist
            dead = [pid for pid in snapshot if not os.path.exists(f"/proc/{pid}")]
            for pid in dead:
                snapshot.pop(pid, None)

            time.sleep(interval)

        except Exception as e:
            emit_event(emitter, "error", "-", "system", "-", f"Error: {str(e)}")
            time.sleep(interval)


# =============================================================
#  ENTRY POINT
# =============================================================
if __name__ == "__main__":
    emitter = EventEmitter()
    monitor_modules(emitter, interval=2)
