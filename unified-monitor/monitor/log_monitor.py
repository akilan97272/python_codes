import time
import platform
import socket
from datetime import datetime
from pathlib import Path
import re


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
#  CLEAN, BASIC, HUMAN-READABLE EMITTER
# =============================================================
class EventEmitter:
    def emit(self, event: Event):
        timestamp = datetime.fromtimestamp(event.ts).strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{event.subtype.upper()}] {timestamp}")
        print(f"File:     {event.data.get('file')}")
        print(f"Message:  {event.data.get('message')}")
        print()  # blank line for readability


# =============================================================
#  SHORTEN MESSAGE (IMPORTANT PART)
# =============================================================
def shorten_message(raw_msg):
    """
    Reduce noisy syslog message to only the human-important part.
    """

    msg = raw_msg

    # Remove ISO timestamps at start
    if re.match(r"\d{4}-\d{2}-\d{2}", msg):
        msg = msg.split(" ", 1)[1]

    # Remove hostname if present
    hostname = socket.gethostname()
    if msg.startswith(hostname + " "):
        msg = msg[len(hostname) + 1:]

    # Remove PID [xxxx]
    msg = re.sub(r"\[\d+\]", "", msg)

    # Keep only message part after first colon
    if ":" in msg:
        msg = msg.split(":", 1)[1].strip()

    # Remove duplicate spaces
    msg = " ".join(msg.split())

    return msg


# =============================================================
#  EMIT EVENT WRAPPER
# =============================================================
def emit_event(emitter, subtype, data):
    event = Event(
        source="log",
        subtype=subtype,
        ts=datetime.now().timestamp(),
        host=socket.gethostname(),
        os=platform.platform(),
        data=data
    )
    emitter.emit(event)


# =============================================================
#  SELECT LOG FILE
# =============================================================
def choose_log_file():
    logfile = "/var/log/syslog"
    if Path(logfile).exists():
        print(f"[log-monitor] Using: {logfile}")
        return logfile
    raise FileNotFoundError("syslog not found")


# =============================================================
#  CLASSIFY SEVERITY
# =============================================================
def classify(line):
    l = line.lower()

    if any(w in l for w in ("error", "failed", "panic", "critical")):
        return "error"
    if any(w in l for w in ("warn", "warning")):
        return "warning"
    if any(w in l for w in ("info", "started", "connected", "listening")):
        return "info"
    return "other"


# =============================================================
#  MAIN LOG MONITOR LOOP
# =============================================================
def monitor_log_file(emitter, logfile=None, interval=0.1):
    logfile = logfile or choose_log_file()

    print(f"[log-monitor] Tailing {logfile}\n")

    with open(logfile, "r", errors="ignore") as f:
        f.seek(0, 2)

        while True:
            line = f.readline()

            if not line:
                time.sleep(interval)
                continue

            line = line.strip()
            if not line:
                continue

            level = classify(line)
            if level == "other":
                continue

            short_msg = shorten_message(line)

            data = {
                "file": logfile,
                "level": level,
                "message": short_msg,
            }

            emit_event(emitter, level, data)


# =============================================================
#  ENTRY POINT
# =============================================================
if __name__ == "__main__":
    emitter = EventEmitter()
    monitor_log_file(emitter)
