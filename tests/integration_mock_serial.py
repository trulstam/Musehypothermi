import os
import json
import tempfile
from typing import List, Dict, Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal

import gui_core_v3


class FakeSerialManager(QObject):
    data_received = Signal(dict)
    raw_line_received = Signal(str)
    raw_line_sent = Signal(str)
    failsafe_triggered = Signal()

    def __init__(self):
        super().__init__()
        self.connected = True
        self.sent_messages: List[str] = []

    def list_ports(self):
        return ["FAKE_PORT"]

    def is_connected(self):
        return self.connected

    def connect(self, port):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False

    def send(self, message: str):
        self.sent_messages.append(message)
        try:
            self.raw_line_sent.emit(message)
        except Exception:
            pass

    def sendCMD(self, action, state, params=None):
        payload = {"CMD": {"action": action, "state": state}}
        if params is not None:
            payload["CMD"]["params"] = params
        self.send(json.dumps(payload))

    def sendSET(self, variable, value):
        self.send(json.dumps({"SET": {"variable": variable, "value": value}}))

    def emit_incoming(self, payload: Dict[str, Any]):
        self.data_received.emit(dict(payload))

    def emit_rx_text(self, text: str):
        self.raw_line_received.emit(text)


# Patch the GUI to use the fake manager
main_window_class = gui_core_v3.MainWindow
gui_core_v3.SerialManager = FakeSerialManager


def run_integration_scenario():
    app = QApplication.instance() or QApplication([])
    window = main_window_class()

    # Simulate an established connection for logging
    window.connection_established = True
    if hasattr(window, "serial_manager"):
        window.serial_manager.connected = True

    fake: FakeSerialManager = window.serial_manager  # type: ignore

    status_payloads = [
        {
            "cooling_plate_temp": 26.5,
            "anal_probe_temp": 25.1,
            "pid_output": 12.5,
            "profile_active": False,
            "profile_step_index": 0,
            "autotune_active": False,
            "equilibrium_valid": False,
            "equilibrium_temp": None,
            "failsafe_active": False,
        },
        {
            "cooling_plate_temp": 32.0,
            "anal_probe_temp": 30.2,
            "pid_output": 30.0,
            "profile_active": True,
            "profile_step_index": 1,
            "autotune_active": True,
            "equilibrium_valid": True,
            "equilibrium_temp": 31.8,
            "failsafe_active": False,
        },
        {
            "cooling_plate_temp": 33.5,
            "anal_probe_temp": 31.5,
            "pid_output": 0.0,
            "profile_active": True,
            "profile_step_index": 2,
            "autotune_active": False,
            "equilibrium_valid": True,
            "equilibrium_temp": 33.1,
            "failsafe_active": True,
            "failsafe_reason": "simulated_overtemp",
        },
    ]

    for idx, payload in enumerate(status_payloads):
        fake.emit_rx_text(f"RX sample line {idx}")
        fake.emit_incoming(payload)
        app.processEvents()

    fake.emit_incoming({"event": "Autotune completed", "autotune_active": False})
    app.processEvents()

    # Validate logging artifacts
    log_files = []
    if getattr(window, "data_logger", None) is not None:
        log_files.append(window.data_logger.filename_csv)
        log_files.append(window.data_logger.filename_json)
        window._stop_data_logger()
    if getattr(window, "event_logger", None) is not None:
        log_files.append(window.event_logger.filename_csv)
        log_files.append(window.event_logger.filename_json)
        window.event_logger.close()

    window.close()
    app.quit()
    return log_files, fake.sent_messages


if __name__ == "__main__":
    files, tx_messages = run_integration_scenario()
    print("Created log files:")
    for path in files:
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        print(f" - {path} (exists={exists}, size={size})")

    print("\nTX messages:")
    for msg in tx_messages:
        print(msg)
