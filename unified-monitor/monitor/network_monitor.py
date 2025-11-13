from .base import BaseMonitor
import time
import platform

try:
    import psutil
except Exception:
    psutil = None

try:
    from scapy.all import sniff
except Exception:
    sniff = None

IS_LINUX = platform.system().lower().startswith("linux")

class NetworkMonitor(BaseMonitor):
    def __init__(self, emitter, iface=None, bpf_filter=None, poll_interval=2.0):
        super().__init__("network", emitter, poll_interval)
        self.iface = iface
        self.bpf_filter = bpf_filter

    def monitor(self):
        if sniff is not None:
            self._monitor_scapy()
        elif psutil is not None:
            self._monitor_psutil_sockets()
        else:
            self.emit("warning", {"msg":"No provider for NetworkMonitor"})

    def _monitor_scapy(self):
        def _cb(pkt):
            if self.stopped():
                return True
            try:
                self.emit("packet", {"summary": str(pkt.summary())})
            except Exception as e:
                self.emit("error", {"stage":"scapy", "err": str(e)})
        sniff(iface=self.iface, prn=_cb, store=False, filter=self.bpf_filter)

    def _monitor_psutil_sockets(self):
        while not self.stopped():
            try:
                conns = psutil.net_connections(kind="inet") if psutil else []
                for c in conns:
                    data = {
                        "fd": c.fd,
                        "family": str(c.family),
                        "type": str(c.type),
                        "laddr": f"{getattr(c.laddr,'ip',None)}:{getattr(c.laddr,'port',None)}" if c.laddr else None,
                        "raddr": f"{getattr(c.raddr,'ip',None)}:{getattr(c.raddr,'port',None)}" if c.raddr else None,
                        "status": c.status,
                        "pid": c.pid
                    }
                    self.emit("socket", data)
                time.sleep(self.poll_interval)
            except Exception as e:
                self.emit("error", {"stage":"psutil_sockets","err":str(e)})
                time.sleep(self.poll_interval)
