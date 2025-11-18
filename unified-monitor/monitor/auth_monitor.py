import time
import platform
import socket
import os
import subprocess
import json
from datetime import datetime

from event import Event
from emitter import EventEmitter

DEFAULT_AUTH_LOG = "/var/log/auth.log"


# =============================================================
# 1. CLASSIFICATION
# =============================================================
def classify(line: str) -> str:
    l = line.lower()

    # SSH
    if "failed password" in l:
        return "ssh_failed_login"
    if "accepted password" in l:
        return "ssh_successful_login"
    if "invalid user" in l:
        return "ssh_invalid_user"

    # SUDO
    if "sudo:" in l and "authentication failure" in l:
        return "sudo_failed_login"
    # NEW: sudo: 3 incorrect password attempts
    if "sudo:" in l and "incorrect password" in l:
        return "sudo_failed_login"
    if "sudo:" in l and "command=" in l:
        return "sudo_success"

    # SU
    if "su[" in l and "(to " in l:
        return "su_switch_user"
    if "su:" in l and "authentication failure" in l:
        return "su_failed_login"
    if "su:" in l and "session opened" in l:
        return "su_success"

    # KEYRING
    if "gkr-pam: unlocked login keyring" in l:
        return "keyring_unlocked"

    # ACCOUNT LOCK/UNLOCK
    if "account locked" in l:
        return "account_locked"
    if "account unlocked" in l:
        return "account_unlocked"

    return "other"


# =============================================================
# 2. FIELD EXTRACTORS
# =============================================================
def extract_user(line: str):
    l = line.lower()

    # SSH login
    if "failed password" in l and " for " in l:
        return l.split("for ")[1].split()[0]
    if "accepted password" in l and " for " in l:
        return l.split("for ")[1].split()[0]

    # SUDO
    if "sudo:" in l:
        try:
            return l.split("sudo:")[1].split(":")[0].strip()
        except Exception:
            return None

    # SU: "root on pts/3"
    if "su[" in l and ") " in l and " on pts" in l:
        try:
            after = l.split("):")[1].strip()
            return after.split()[0]
        except Exception:
            return None

    # SU success
    if "session opened for user" in l:
        try:
            return l.split("session opened for user")[1].split("(")[0].strip()
        except Exception:
            return None

    return None


def extract_target_user(line: str):
    if "(to " in line:
        try:
            return line.split("(to ")[1].split(")")[0]
        except Exception:
            return None
    return None


def extract_ip(line: str):
    l = line.lower()
    if " from " in l:
        try:
            return l.split("from ")[1].split()[0]
        except Exception:
            return None
    return None


def extract_tty(line: str):
    l = line.lower()

    if "tty=" in l:
        return l.split("tty=")[1].split()[0]

    if " on pts/" in l:
        return "pts/" + l.split("pts/")[1].split()[0]

    return None


def extract_command(line: str):
    if "COMMAND=" in line:
        try:
            return line.split("COMMAND=")[1].split()[0]
        except Exception:
            return None
    return None


def extract_attempts(line: str):
    """
    For lines like: 'sudo: 3 incorrect password attempts'
    """
    l = line.lower()
    if "incorrect password" in l and "sudo:" in l:
        try:
            # e.g. "sudo: 3 incorrect password attempts"
            after = l.split("sudo:")[1].strip()
            num = after.split()[0]
            return int(num)
        except Exception:
            return None
    return None


# =============================================================
# 3. NORMALIZATION (SUCCESS/FAIL, CHANNEL, CATEGORY, REASON)
# =============================================================
def normalize_fields(subtype: str, parsed: dict) -> dict:
    # Channel
    if subtype.startswith("ssh_"):
        parsed["channel"] = "ssh"
    elif subtype.startswith("sudo_"):
        parsed["channel"] = "sudo"
    elif subtype.startswith("su_"):
        parsed["channel"] = "su"
    elif "keyring" in subtype:
        parsed["channel"] = "keyring"
    elif "account_" in subtype:
        parsed["channel"] = "account"
    else:
        parsed["channel"] = "other"

    # Success / Fail
    if "failed" in subtype:
        parsed["success"] = False
    elif "successful" in subtype or subtype in ("su_success", "sudo_success"):
        parsed["success"] = True
    else:
        parsed["success"] = None

    # Category
    if "login" in subtype:
        parsed["category"] = "login"
    elif "switch_user" in subtype:
        parsed["category"] = "session"
    elif "keyring" in subtype:
        parsed["category"] = "key_management"
    elif "account_" in subtype:
        parsed["category"] = "account_state"
    else:
        parsed["category"] = "other"

    # Reason for failures
    if parsed["success"] is False:
        parsed["reason"] = "wrong_password"

    return parsed


# =============================================================
# 4. BUILD EVENT DATA
# =============================================================
def build_event_data(subtype: str, raw_line: str, journal_entry: dict | None = None) -> dict:
    parsed = {
        "user": extract_user(raw_line),
        "target": extract_target_user(raw_line),
        "ip": extract_ip(raw_line),
        "tty": extract_tty(raw_line),
        "command": extract_command(raw_line),
        "attempts": extract_attempts(raw_line),
    }

    parsed = normalize_fields(subtype, parsed)

    data = {
        "subtype": subtype,
        "raw_line": raw_line,
        "host": socket.gethostname(),
        "os": platform.platform(),
        **parsed,
    }

    if journal_entry is not None:
        data["journal_meta"] = journal_entry

    return data


# =============================================================
# 5. CLEAN, HUMAN-READABLE OUTPUT
# =============================================================
def print_clean(subtype: str, data: dict):
    parts = ["AUTH"]

    dt = data.get("datetime")
    if dt:
        parts.append(f"time={dt}")

    parts.append(f"event={subtype}")

    for key in ["channel", "success", "user", "target", "ip", "tty", "command", "attempts", "reason"]:
        v = data.get(key)
        if v is not None:
            parts.append(f"{key}={v}")

    print(" | ".join(parts))


# =============================================================
# 6. EMIT
# =============================================================
def emit_event(emitter: EventEmitter, subtype: str, data: dict):
    ts = time.time()
    data["ts"] = ts
    data["datetime"] = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    # Console
    print_clean(subtype, data)

    # Backend event
    event = Event(
        source="auth",
        subtype=subtype,
        ts=ts,
        host=data["host"],
        os=data["os"],
        data=data,
    )

    emitter.emit(event)


# =============================================================
# 7. FILE BACKEND (/var/log/auth.log)
# =============================================================
def monitor_auth_file(emitter: EventEmitter, logfile: str = DEFAULT_AUTH_LOG):
    print(f"AUTH | info | monitoring={logfile}")

    with open(logfile, "r") as f:
        f.seek(0, os.SEEK_END)  # start at end

        while True:
            line = f.readline()
            if not line:
                time.sleep(0.2)
                continue

            clean = line.strip()
            subtype = classify(clean)

            # skip noise
            if subtype == "other":
                continue

            data = build_event_data(subtype, clean)
            emit_event(emitter, subtype, data)


# =============================================================
# 8. JOURNAL BACKEND (Kali, etc.)
# =============================================================
def monitor_auth_journal(emitter: EventEmitter):
    print("AUTH | info | monitoring=journalctl (systemd journal)")

    cmd = ["journalctl", "-f", "-o", "json"]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    while True:
        line = process.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg = entry.get("MESSAGE", "")

        # handle list / weird types safely
        if isinstance(msg, list):
            msg = " ".join(str(x) for x in msg)
        else:
            msg = str(msg)

        clean = msg.strip()
        if not clean:
            continue

        # basic auth-related filter to drop random system noise
        low = clean.lower()
        if not any(k in low for k in ["ssh", "sudo", "su", "authentication", "pam", "keyring", "account"]):
            continue

        subtype = classify(clean)

        # skip "other" events: you said you don't want them
        if subtype == "other":
            continue

        data = build_event_data(subtype, clean, journal_entry=entry)
        emit_event(emitter, subtype, data)


# =============================================================
# 9. WRAPPER
# =============================================================
def monitor_auth(emitter: EventEmitter, logfile: str = DEFAULT_AUTH_LOG):
    if os.path.exists(logfile):
        print(f"AUTH | info | {logfile} found, using file backend")
        monitor_auth_file(emitter, logfile)
    else:
        print(f"AUTH | warning | {logfile} not found, using systemd journal instead")
        monitor_auth_journal(emitter)


# =============================================================
# 10. MAIN
# =============================================================
if __name__ == "__main__":
    emitter = EventEmitter(out="silent", output_format="silent")
    monitor_auth(emitter)