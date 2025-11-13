import time
from monitor.emitter import EventEmitter
from monitor.process_monitor import ProcessMonitor
from monitor.network_monitor import NetworkMonitor
from monitor.fs_monitor import FSMonitor
from monitor.registry_monitor import RegistryMonitor
from monitor.log_monitor import LogMonitor
from monitor.module_monitor import ModuleMonitor
from monitor.auth_monitor import AuthMonitor

# -----------------------------
# SWITCH-CASE STYLE DISPATCH MAP
# -----------------------------
def get_monitor_factory(choice: str, emitter: EventEmitter):
    """
    Returns a factory (callable) that produces a list of monitors for a given choice.
    We return a callable so we create monitor instances *after* the user picks options.
    """
    choices = {
        "1": lambda: [ProcessMonitor(emitter)],
        "2": lambda: [FSMonitor(emitter, paths=["~"])],
        "3": lambda: [NetworkMonitor(emitter)],
        "4": lambda: [ModuleMonitor(emitter)],
        "5": lambda: [AuthMonitor(emitter)],
        "6": lambda: [LogMonitor(emitter)],
        "7": lambda: [RegistryMonitor(emitter)],
        "8": lambda: [
            ProcessMonitor(emitter),
            FSMonitor(emitter, paths=["~"]),
            NetworkMonitor(emitter),
            ModuleMonitor(emitter),
            AuthMonitor(emitter),
            LogMonitor(emitter),
            RegistryMonitor(emitter),
        ],
    }
    return choices.get(choice)


# -----------------------------
# MAIN
# -----------------------------
def main():
    print("===== Unified Monitor Switch Menu =====")
    print("1 - Process Monitor")
    print("2 - File System Monitor")
    print("3 - Network Monitor")
    print("4 - Module Monitor")
    print("5 - Auth Monitor")
    print("6 - Log Monitor")
    print("7 - Registry Monitor")
    print("8 - Run ALL Monitors")
    print("=======================================")
    raw = input("Enter your choice (1-8) or comma-list (e.g. 1,3,5): ").strip()

    # support "1" or "1,3,5"
    selected = [s.strip() for s in raw.split(",") if s.strip()]
    if not selected:
        print("No selection, exiting.")
        return

    emitter = EventEmitter(out="stdout", output_format="table")

    # collect factories for each selected choice
    factories = []
    for ch in selected:
        fac = get_monitor_factory(ch, emitter)
        if fac is None:
            print(f"Invalid choice: {ch}. Skipping.")
            continue
        factories.append(fac)

    if not factories:
        print("No valid monitors selected. Exiting.")
        return

    # create instances by calling factories and flatten
    monitor_list = []
    for fac in factories:
        try:
            insts = fac()
            if isinstance(insts, list):
                monitor_list.extend(insts)
            else:
                # if factory returned a single monitor instance
                monitor_list.append(insts)
        except Exception as e:
            print(f"Failed to instantiate monitor for factory {fac}: {e}")

    if not monitor_list:
        print("No monitors instantiated. Exiting.")
        return

    print(f"\nStarting monitors for choices: {', '.join(selected)}...\n")

    # Start selected monitors
    for m in monitor_list:
        m.start()

    print("Running... Press CTRL + C to stop.\n")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping monitors...")
        for m in monitor_list:
            m.stop()
        for m in monitor_list:
            m.join()
        emitter.close()
        print("All monitors stopped.")


if __name__ == "__main__":
    main()
