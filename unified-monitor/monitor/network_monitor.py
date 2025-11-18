# network_monitor_fn.py

import subprocess
import time
import platform
import socket
from datetime import datetime

from event import Event
from emitter import EventEmitter


# -------------------------------------------------------------
# CLEAN PRINT (C FORMAT)
# -------------------------------------------------------------
def print_clean(subtype, data):
    parts = [f"NETWORK | {subtype}"]
    for k, v in data.items():
        if v is not None:
            parts.append(f"{k}={v}")
    print(" | ".join(parts))


# -------------------------------------------------------------
# EMIT EVENT (clean stdout + silent emitter)
# -------------------------------------------------------------
def emit_event(emitter: EventEmitter, subtype: str, data: dict):
    print_clean(subtype, data)

    event = Event(
        source="network",
        subtype=subtype,
        ts=datetime.now().timestamp(),
        host=socket.gethostname(),
        os=platform.platform(),
        data=data,
    )
    emitter.emit(event)


# -------------------------------------------------------------
# GET CURRENT CONNECTION SNAPSHOT
# -------------------------------------------------------------
def get_connections():
    """
    Use `ss -aH` to list sockets, and return a set of:
      (proto, state, local, remote, path)

    We keep:
      - TCP connections
      - UDP connections
      - UNIX sockets that have a real filesystem path

    We ignore:
      - netlink / tcpdiag / kernel-internal junk
      - weird entries like ->*
    """
    out = subprocess.check_output(
        ["ss", "-aH"],           # all sockets, no header
        text=True,
        stderr=subprocess.DEVNULL,
    )

    lines = out.strip().splitlines()
    conns = set()

    for line in lines:
        parts = line.split()
        if len(parts) < 4:
            continue

        proto = parts[0].lower()
        state = parts[1].lower()

        # skip kernel-internal junk
        if proto in ["nl", "netlink", "tcpdiag"]:
            continue
        if "tcpdiag" in line:
            continue
        if "->*" in line:
            continue

        # UNIX sockets: only keep with real path
        if proto in ["unix", "u_str", "u_dgr", "u_seq", "xdp"]:
            path = parts[-1]
            if path.startswith("/"):
                conns.add((
                    "unix",
                    state,
                    None,
                    None,
                    path,
                ))
            continue

        # keep only TCP/UDP for now (simpler + enough)
        if proto not in ["tcp", "udp"]:
            continue

        try:
            local = parts[-2]
            remote = parts[-1]
        except IndexError:
            continue

        conns.add((
            proto,
            state,
            local,
            remote,
            None,
        ))

    return conns


# -------------------------------------------------------------
# MAIN MONITOR LOOP
# -------------------------------------------------------------
def monitor_network(emitter: EventEmitter, interval: int = 3):
    """
    Every `interval` seconds:
      - take a snapshot of connections
      - log only *new* connections since last snapshot
    """
    if platform.system().lower() != "linux":
        emit_event(emitter, "error", {"msg": "network monitor works only on linux"})
        return

    print("NETWORK | info | monitoring=new_connections_only")

    prev = set()

    while True:
        curr = get_connections()

        # Only log *new* connections
        new = curr - prev
        for (proto, state, local, remote, path) in new:
            data = {
                "proto": proto,
                "state": state,
                "local": local,
                "remote": remote,
                "path": path,
            }
            emit_event(emitter, "connection", data)

        prev = curr
        time.sleep(interval)


# -------------------------------------------------------------
# RUN
# -------------------------------------------------------------
if __name__ == "__main__":
    emitter = EventEmitter(out="silent", output_format="silent")
    monitor_network(emitter)