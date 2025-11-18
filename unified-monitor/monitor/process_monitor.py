# process_monitor_fn.py

import subprocess
import time
import platform
import socket
from datetime import datetime

from emitter import EventEmitter
from event import Event


# -------------------------------------------------------------
# PRINT CLEAN OUTPUT (C FORMAT — same as AUTH)
# -------------------------------------------------------------
def print_clean(subtype, data):
    parts = [f"PROCESS | {subtype}"]
    for key, value in data.items():
        if value is not None:
            parts.append(f"{key}={value}")
    print(" | ".join(parts))


# -------------------------------------------------------------
# EMIT EVENT (silent emitter + clean stdout)
# -------------------------------------------------------------
def emit_event(emitter: EventEmitter, subtype: str, data: dict):
    print_clean(subtype, data)

    event = Event(
        source="process",
        subtype=subtype,
        ts=datetime.now().timestamp(),
        host=socket.gethostname(),
        os=platform.platform(),
        data=data,
    )

    emitter.emit(event)     # silent emitter → NO table, NO dict, NO fallback


# -------------------------------------------------------------
# TAKE A SNAPSHOT OF CURRENT PROCESSES
# -------------------------------------------------------------
def get_process_snapshot() -> dict:
    """
    Returns a dict: { pid: name }
    Uses Linux `ps` command.
    """
    out = subprocess.check_output(["ps", "-eo", "pid,comm"], text=True)

    lines = out.strip().splitlines()
    if not lines:
        return {}

    # skip header ("PID COMMAND")
    lines = lines[1:]

    snapshot = {}

    for line in lines:
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue

        pid_str, name = parts

        # ignore "ps" command itself (avoid infinite spam)
        if name == "ps":
            continue

        try:
            pid = int(pid_str)
        except ValueError:
            continue

        snapshot[pid] = name

    return snapshot


# -------------------------------------------------------------
# MAIN PROCESS MONITOR LOOP
# -------------------------------------------------------------
def monitor_processes(emitter: EventEmitter, interval: int = 3):
    if platform.system().lower() != "linux":
        emit_event(emitter, "error", {"msg": "Process monitor only supports Linux"})
        return

    print("PROCESS | info | monitoring=process_list")

    prev = {}

    while True:
        curr = get_process_snapshot()

        prev_pids = set(prev.keys())
        curr_pids = set(curr.keys())

        # New processes
        for pid in curr_pids - prev_pids:
            emit_event(
                emitter,
                "start",
                {"pid": pid, "name": curr.get(pid)},
            )

        # Terminated processes
        for pid in prev_pids - curr_pids:
            emit_event(
                emitter,
                "end",
                {"pid": pid, "name": prev.get(pid)},
            )

        prev = curr
        time.sleep(interval)


# -------------------------------------------------------------
# RUN
# -------------------------------------------------------------
if __name__ == "__main__":
    # SILENT emitter → only clean PROCESS lines, no duplicates
    emitter = EventEmitter(out="silent", output_format="silent")
    monitor_processes(emitter, interval=3)