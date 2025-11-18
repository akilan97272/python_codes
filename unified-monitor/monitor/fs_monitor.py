#!/usr/bin/env python3

import subprocess
import time
import socket
import platform
from datetime import datetime


# Directories we usually DON'T want to walk (too noisy / virtual)
EXCLUDE_DIRS = {
    "/proc",
    "/sys",
    "/dev",
    "/run",
    "/var/lib/docker",
    "/snap",
}


# =============================================================
#  HUMAN-READABLE EVENT PRINTER
# =============================================================
def print_event(event_type, path, extra=None):
    """
    Print a simple, human-readable filesystem event.
    event_type: "CREATED", "DELETED", "MODIFIED", "INFO", "ERROR"
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{event_type}] {ts}")
    print(f"Path:     {path}")
    if extra:
        for k, v in extra.items():
            print(f"{k}: {v}")
    print()  # blank line for readability


# =============================================================
#  BUILD SNAPSHOT USING LINUX 'find'
# =============================================================
def build_snapshot(paths, exclude_dirs=None):
    """
    Use Linux 'find' command to build a snapshot of files.

    Returns:
        { path: (mtime_float, size_int) }
    """
    snapshot = {}
    exclude_dirs = exclude_dirs or set()

    # Prepare the base 'find' command:
    # find <paths...> \( -path /proc -o -path /sys ... \) -prune -o -type f -printf '%p|%T@|%s\n'
    cmd = ["find"]
    cmd.extend(paths)

    # Exclusion part
    if exclude_dirs:
        cmd.append("(")
        first = True
        for d in sorted(exclude_dirs):
            if not first:
                cmd.append("-o")
            cmd.extend(["-path", d])
            first = False
        cmd.extend([")", "-prune", "-o"])

    # Only files, print "path|mtime|size"
    cmd.extend(["-type", "f", "-printf", "%p|%T@|%s\n"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
    except Exception as e:
        print_event("ERROR", "-", {"Error": f"Failed to run find: {e}"})
        return snapshot

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue

        # path|mtime|size
        parts = line.rsplit("|", 2)
        if len(parts) != 3:
            continue

        path, mtime_str, size_str = parts
        try:
            mtime = float(mtime_str)
            size = int(size_str)
        except ValueError:
            continue

        snapshot[path] = (mtime, size)

    return snapshot


# =============================================================
#  MAIN FS MONITOR LOOP
# =============================================================
def monitor_fs(paths=None, interval=5):
    """
    Polling-based filesystem monitor using Linux 'find'.

    If `paths` is None:
      - It will watch: /home, /etc, /var/log

    Detects:
      - File created
      - File deleted
      - File modified
    """
    if platform.system().lower() != "linux":
        print_event("ERROR", "-", {"Error": "FS monitor only supports Linux"})
        return

    if not paths:
        paths = ["/home", "/etc", "/var/log"]

    # Normalize paths
    paths = list(dict.fromkeys(paths))  # remove duplicates, keep order

    print_event(
        "INFO",
        ", ".join(paths),
        {
            "Host": socket.gethostname(),
            "OS": platform.platform(),
            "Interval (sec)": interval,
            "Note": "Using 'find' command for filesystem snapshot",
        },
    )

    prev = build_snapshot(paths, exclude_dirs=EXCLUDE_DIRS)

    while True:
        time.sleep(interval)
        curr = build_snapshot(paths, exclude_dirs=EXCLUDE_DIRS)

        prev_paths = set(prev.keys())
        curr_paths = set(curr.keys())

        # ---------------- NEW FILES ----------------
        created = curr_paths - prev_paths
        for path in created:
            mtime, size = curr[path]
            extra = {
                "Size (bytes)": size,
                "Modified": datetime.fromtimestamp(mtime).isoformat(timespec="seconds"),
            }
            print_event("CREATED", path, extra)

        # ---------------- DELETED FILES ----------------
        deleted = prev_paths - curr_paths
        for path in deleted:
            mtime, size = prev[path]
            extra = {
                "Last known size": size,
                "Last modified": datetime.fromtimestamp(mtime).isoformat(timespec="seconds"),
            }
            print_event("DELETED", path, extra)

        # ---------------- MODIFIED FILES ----------------
        common = prev_paths & curr_paths
        for path in common:
            old_mtime, old_size = prev[path]
            new_mtime, new_size = curr[path]

            if old_mtime != new_mtime or old_size != new_size:
                extra = {
                    "Old size": old_size,
                    "New size": new_size,
                    "Old mtime": datetime.fromtimestamp(old_mtime).isoformat(timespec="seconds"),
                    "New mtime": datetime.fromtimestamp(new_mtime).isoformat(timespec="seconds"),
                }
                print_event("MODIFIED", path, extra)

        prev = curr


# =============================================================
#  ENTRY POINT
# =============================================================
if __name__ == "__main__":
    # Default: monitor key system locations
    monitor_fs(paths=None, interval=5)
