import json
import socket
import time
from datetime import datetime


class EventEmitter:
    """
    Outputs monitoring events in JSON, Table, C-style, or Silent mode.

    output_format:
      - "table"  -> pipe-style table rows
      - "json"   -> pretty JSON per event
      - "c"      -> monitors print their own C-style lines; emitter stays quiet
      - "silent" -> no output
    """

    def __init__(self, out="stdout", output_format="table"):
        self.output_format = output_format.lower()
        self.out = out
        self.hostname = socket.gethostname()

        # Don't print emitter startup in silent mode
        if self.output_format != "silent" and self.out != "silent":
            print(f"[Emitter] Output: {self.output_format}, Target: {self.out}")

    def emit(self, event):
        """Emit event based on selected output format."""

        # --- FULL SILENT MODE ---
        if self.output_format == "silent" or self.out == "silent":
            return  # do nothing, completely silent

        # ------ JSON MODE ------
        if self.output_format == "json":
            print(
                json.dumps(
                    {
                        "timestamp": event.ts,
                        "datetime": datetime.fromtimestamp(event.ts).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "host": event.host,
                        "source": event.source,
                        "subtype": event.subtype,
                        "data": event.data,
                    },
                    indent=2,
                )
            )
            return

        # ----- TABLE MODE -----
        if self.output_format == "table":
            print(
                f"| {datetime.fromtimestamp(event.ts).strftime('%Y-%m-%d %H:%M:%S')} | "
                f"{event.source} | {event.subtype} | {event.data} |"
            )
            return

        # ----- C-STYLE MODE -----
        if self.output_format == "c":
            # In "c" mode, individual monitors (fs, process, etc.) already
            # print C-style lines like:
            #   FS | modified | path=... | ...
            #
            # So we don't print anything here to avoid duplicates.
            return

        # FALLBACK (should not happen now)
        print("[Emitter] Unknown format, event:")
        print(event)

    def close(self):
        if self.output_format != "silent" and self.out != "silent":
            print("[Emitter] Shutdown complete.")