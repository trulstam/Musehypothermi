import os

# Use offscreen platform before importing Qt to avoid display and GL requirements
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from framework.serial_comm import SerialManager  # noqa: E402
from framework.profile_loader import ProfileLoader  # noqa: E402
from framework.event_logger import EventLogger  # noqa: E402
from framework.logger import Logger  # noqa: E402
from gui_core_v3 import MainWindow  # noqa: E402


def run_smoke_test():
    app = QApplication.instance() or QApplication([])

    # Ensure managers can be instantiated
    serial_manager = SerialManager()
    _ = ProfileLoader
    _ = EventLogger
    _ = Logger

    window = MainWindow()

    fake_payload = {
        "plate_temp": 33.2,
        "rectal_temp": 32.5,
        "pid_output": 45.0,
        "breath_rate": 0,
        "target_temp": 34.0,
        "rectal_target_temp": 33.5,
        "failsafe_active": False,
        "failsafe_reason": "",
        "equilibriumTemp": 33.7,
        "equilibriumValid": True,
    }

    # Simulate incoming data
    window.process_incoming_data(fake_payload)

    # Process pending events briefly
    app.processEvents()

    window.close()
    app.quit()


if __name__ == "__main__":
    run_smoke_test()
    print("Smoke test completed")
