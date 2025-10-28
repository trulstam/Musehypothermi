import sys
import json
import time
import csv
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel,
    QVBoxLayout, QWidget, QFileDialog, QHBoxLayout,
    QTextEdit, QComboBox, QMessageBox, QGroupBox,
    QFormLayout, QLineEdit, QSplitter
)
from PySide6.QtCore import QTimer, Qt
import pyqtgraph as pg
from serial_comm import SerialManager
from event_logger import EventLogger
from profile_graph_widget import ProfileGraphPopup

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Musehypothermi GUI - Status Monitor")
        self.resize(1400, 900)

        self.serial_manager = SerialManager()
        self.serial_manager.on_data_received = self.process_incoming_data

        self.event_logger = EventLogger("gui_events")

        self.status_request_timer = QTimer()
        self.status_request_timer.timeout.connect(self.request_status)
        self.status_request_timer.start(5000)

        self.profile_data = []

        self.init_ui()

        self.graph_data = {
            "time": [],
            "plate_temp": [],
            "rectal_temp": [],
            "pid_output": [],
            "breath_rate": [],
            "target_temp": []
        }

    def init_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout()

        serial_control_layout = QHBoxLayout()
        self.portSelector = QComboBox()
        self.refresh_ports()
        self.refreshButton = QPushButton("Refresh Ports")
        self.refreshButton.clicked.connect(self.refresh_ports)
        self.connectButton = QPushButton("Connect")
        self.connectButton.clicked.connect(self.toggle_connection)
        serial_control_layout.addWidget(QLabel("Serial Port:"))
        serial_control_layout.addWidget(self.portSelector)
        serial_control_layout.addWidget(self.refreshButton)
        serial_control_layout.addWidget(self.connectButton)
        left_layout.addLayout(serial_control_layout)

        status_group = QGroupBox("System Status")
        status_layout = QFormLayout()
        self.connectionStatusLabel = QLabel("Disconnected")
        self.failsafeLabel = QLabel("None")
        self.profileStatusLabel = QLabel("Inactive")
        self.autotuneStatusLabel = QLabel("Idle")
        self.maxOutputLabel = QLabel("Unknown")
        self.pidParamsLabel = QLabel("Kp: -, Ki: -, Kd: -")

        status_layout.addRow("Connection Status:", self.connectionStatusLabel)
        status_layout.addRow("Failsafe:", self.failsafeLabel)
        status_layout.addRow("Profile:", self.profileStatusLabel)
        status_layout.addRow("Autotune:", self.autotuneStatusLabel)
        status_layout.addRow("Max Output Limit:", self.maxOutputLabel)
        status_layout.addRow("PID Params:", self.pidParamsLabel)

        self.saveEEPROMButton = QPushButton("Save PID to EEPROM")
        self.saveEEPROMButton.clicked.connect(self.save_pid_to_eeprom)
        status_layout.addRow("", self.saveEEPROMButton)
        status_group.setLayout(status_layout)
        left_layout.addWidget(status_group)

        pid_input_group = QGroupBox("Manual PID Input")
        pid_input_layout = QHBoxLayout()
        self.kpInput = QLineEdit()
        self.kiInput = QLineEdit()
        self.kdInput = QLineEdit()
        self.setPIDButton = QPushButton("Set PID Values")
        self.setPIDButton.clicked.connect(self.set_pid_values)
        pid_input_layout.addWidget(QLabel("Kp:"))
        pid_input_layout.addWidget(self.kpInput)
        pid_input_layout.addWidget(QLabel("Ki:"))
        pid_input_layout.addWidget(self.kiInput)
        pid_input_layout.addWidget(QLabel("Kd:"))
        pid_input_layout.addWidget(self.kdInput)
        pid_input_layout.addWidget(self.setPIDButton)
        pid_input_group.setLayout(pid_input_layout)
        left_layout.addWidget(pid_input_group)

        setpoint_group = QGroupBox("Manual Setpoint")
        setpoint_layout = QHBoxLayout()
        self.setpointInput = QLineEdit()
        self.setSetpointButton = QPushButton("Set Target Temp")
        self.setSetpointButton.clicked.connect(self.set_manual_setpoint)
        setpoint_layout.addWidget(QLabel("Target Temp:"))
        setpoint_layout.addWidget(self.setpointInput)
        setpoint_layout.addWidget(self.setSetpointButton)
        setpoint_group.setLayout(setpoint_layout)
        left_layout.addWidget(setpoint_group)

        control_group = QGroupBox("Controls")
        control_layout = QHBoxLayout()
        self.startPIDButton = QPushButton("Start PID")
        self.startPIDButton.clicked.connect(lambda: self.serial_manager.sendCMD("pid", "start"))
        self.stopPIDButton = QPushButton("Stop PID")
        self.stopPIDButton.clicked.connect(lambda: self.serial_manager.sendCMD("pid", "stop"))
        self.startProfileButton = QPushButton("Start Profile")
        self.startProfileButton.clicked.connect(lambda: self.serial_manager.sendCMD("profile", "start"))
        self.pauseProfileButton = QPushButton("Pause Profile")
        self.pauseProfileButton.clicked.connect(lambda: self.serial_manager.sendCMD("profile", "pause"))
        self.resumeProfileButton = QPushButton("Resume Profile")
        self.resumeProfileButton.clicked.connect(lambda: self.serial_manager.sendCMD("profile", "resume"))
        self.stopProfileButton = QPushButton("Stop Profile")
        self.stopProfileButton.clicked.connect(lambda: self.serial_manager.sendCMD("profile", "stop"))
        self.loadProfileButton = QPushButton("Load Profile")
        self.loadProfileButton.clicked.connect(self.load_profile)
        self.viewProfileButton = QPushButton("View Profile Graph")
        self.viewProfileButton.clicked.connect(self.open_profile_graph_popup)
        self.panicButton = QPushButton("PANIC")
        self.panicButton.setFixedSize(100, 100)
        self.panicButton.setStyleSheet("border-radius: 50px; background-color: red; color: white; font-weight: bold;")
        self.panicButton.clicked.connect(self.trigger_panic)
        self.clearFailsafeButton = QPushButton("Clear Failsafe")
        self.clearFailsafeButton.setStyleSheet("background-color: orange; font-weight: bold;")
        self.clearFailsafeButton.clicked.connect(self.clear_failsafe)

        for btn in [self.startPIDButton, self.stopPIDButton, self.startProfileButton,
                    self.pauseProfileButton, self.resumeProfileButton, self.stopProfileButton,
                    self.loadProfileButton, self.viewProfileButton, self.panicButton, self.clearFailsafeButton]:
            control_layout.addWidget(btn)

        control_group.setLayout(control_layout)
        left_layout.addWidget(control_group)
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        self.logBox = QTextEdit()
        self.logBox.setReadOnly(True)
        log_widget = QWidget()
        log_layout = QVBoxLayout()
        log_layout.addWidget(QLabel("Event Log"))
        log_layout.addWidget(self.logBox)
        log_widget.setLayout(log_layout)
        splitter.addWidget(log_widget)

        graph_group = QGroupBox("Live Graphs")
        graph_layout = QVBoxLayout()
        self.tempGraphWidget = pg.PlotWidget(title="Temperatures")
        self.tempGraphWidget.addLegend()
        self.temp_plot_plate = self.tempGraphWidget.plot(pen='y', name="Cooling Plate")
        self.temp_plot_rectal = self.tempGraphWidget.plot(pen='r', name="Rectal Probe")
        self.temp_plot_target = self.tempGraphWidget.plot(pen='g', name="Target Temp")

        self.pidGraphWidget = pg.PlotWidget(title="PID Output")
        self.pidGraphWidget.addLegend()
        self.pid_plot = self.pidGraphWidget.plot(pen='g', name="PID Output")

        self.breathGraphWidget = pg.PlotWidget(title="Breath Frequency")
        self.breathGraphWidget.addLegend()
        self.breath_plot = self.breathGraphWidget.plot(pen='c', name="Breath Rate")

        graph_layout.addWidget(self.tempGraphWidget)
        graph_layout.addWidget(self.pidGraphWidget)
        graph_layout.addWidget(self.breathGraphWidget)
        graph_group.setLayout(graph_layout)

        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.addWidget(splitter)
        container_layout.addWidget(graph_group)
        container.setLayout(container_layout)
        self.setCentralWidget(container)

    def log(self, message):
        self.logBox.append(message)
        print(f"LOG: {message}")

    def process_incoming_data(self, data):
        if not data:
            return

        if "response" in data:
            self.log(f"✅ Controller ACK: {data['response']}")

        telemetry_keys = (
            "cooling_plate_temp",
            "anal_probe_temp",
            "pid_output",
            "breath_freq_bpm",
            "plate_target_active",
        )

        if any(key in data for key in telemetry_keys):
            now = time.time()
            last_or_default = lambda series, default=0: series[-1] if series else default

            self.graph_data["time"].append(now)
            self.graph_data["plate_temp"].append(data.get("cooling_plate_temp", last_or_default(self.graph_data["plate_temp"])))
            self.graph_data["rectal_temp"].append(data.get("anal_probe_temp", last_or_default(self.graph_data["rectal_temp"])))
            self.graph_data["pid_output"].append(data.get("pid_output", last_or_default(self.graph_data["pid_output"])))
            self.graph_data["breath_rate"].append(data.get("breath_freq_bpm", last_or_default(self.graph_data["breath_rate"])))
            self.graph_data["target_temp"].append(data.get("plate_target_active", last_or_default(self.graph_data["target_temp"])))

            for key in self.graph_data:
                if len(self.graph_data[key]) > 200:
                    self.graph_data[key] = self.graph_data[key][-200:]

            self.temp_plot_plate.setData(self.graph_data["time"], self.graph_data["plate_temp"])
            self.temp_plot_rectal.setData(self.graph_data["time"], self.graph_data["rectal_temp"])
            self.temp_plot_target.setData(self.graph_data["time"], self.graph_data["target_temp"])
            self.pid_plot.setData(self.graph_data["time"], self.graph_data["pid_output"])
            self.breath_plot.setData(self.graph_data["time"], self.graph_data["breath_rate"])

        if "event" in data:
            event_msg = data["event"]
            self.log(f"📢 EVENT: {event_msg}")
            self.event_logger.log_event(event_msg)

    def open_profile_graph_popup(self):
        self.profile_popup = ProfileGraphPopup(self.profile_data)
        self.profile_popup.show()

    def set_manual_setpoint(self):
        try:
            value = float(self.setpointInput.text())
            self.serial_manager.sendSET("target_temp", value)
            self.log(f"✅ Manual setpoint set to {value:.2f} °C")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for target temperature.")

    def load_profile(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Profile", "", "JSON Files (*.json);;CSV Files (*.csv)")
        if file_name:
            try:
                steps, profile_points = self.parse_profile_file(file_name)
            except ValueError as exc:
                QMessageBox.warning(self, "Load Error", str(exc))
                return

            self.profile_data = profile_points
            self.log(f"Loaded profile: {file_name}")

            if steps:
                self.serial_manager.sendSET("profile", steps)
                self.log(f"📤 Uploaded {len(steps)} profile steps to controller")
            else:
                self.log("⚠️ Profile did not contain structured steps; upload skipped")

    def parse_profile_file(self, path):
        try:
            suffix = Path(path).suffix.lower()
            if suffix == ".json":
                return self._parse_json_profile(path)
            if suffix == ".csv":
                return self._parse_csv_profile(path)
            raise ValueError("Unsupported profile format. Use JSON or CSV.")
        except OSError as exc:
            raise ValueError(f"Failed to load profile file: {exc}") from exc

    def _parse_json_profile(self, path):
        with open(path, "r", encoding="utf-8") as file:
            raw_data = json.load(file)

        if not isinstance(raw_data, list):
            raise ValueError("Profile JSON must be a list of steps")

        steps = []
        for index, entry in enumerate(raw_data, start=1):
            if not isinstance(entry, dict):
                raise ValueError(f"Profile step #{index} is not an object")

            try:
                start_temp = float(entry["plate_start_temp"])
                end_temp = float(entry["plate_end_temp"])
                total_ms = int(float(entry["total_step_time_ms"]))
            except KeyError as exc:
                raise ValueError(f"Profile step #{index} missing field: {exc}") from exc
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Profile step #{index} has invalid numeric value") from exc

            ramp_ms = int(float(entry.get("ramp_time_ms", 0)))
            rectal_override = float(entry.get("rectal_override_target", -1000.0))

            if total_ms <= 0:
                raise ValueError(f"Profile step #{index} duration must be positive")

            ramp_ms = max(0, min(ramp_ms, total_ms))

            steps.append({
                "plate_start_temp": start_temp,
                "plate_end_temp": end_temp,
                "ramp_time_ms": ramp_ms,
                "rectal_override_target": rectal_override,
                "total_step_time_ms": total_ms,
            })

        if len(steps) > 10:
            raise ValueError("Profile may contain at most 10 steps")

        graph_points = self._steps_to_graph_points(steps)
        return steps, graph_points

    def _parse_csv_profile(self, path):
        rows = []
        with open(path, newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if not row:
                    continue
                if row[0].startswith("#"):
                    continue
                try:
                    time_min = float(row[0])
                    temp_c = float(row[1])
                    ramp_min = float(row[2]) if len(row) > 2 else 0.0
                except (ValueError, IndexError):
                    continue
                rows.append((time_min, temp_c, ramp_min))

        if len(rows) < 2:
            raise ValueError("CSV profile must contain at least two rows of data")

        steps = []
        for idx in range(1, len(rows)):
            prev_time, prev_temp, _ = rows[idx - 1]
            current_time, current_temp, ramp_min = rows[idx]

            duration_min = max(current_time - prev_time, 0)
            total_ms = int(duration_min * 60000)
            if total_ms <= 0:
                raise ValueError(f"Row {idx + 1} time must be greater than previous row")

            ramp_ms = int(max(0.0, min(ramp_min, duration_min)) * 60000)

            steps.append({
                "plate_start_temp": prev_temp,
                "plate_end_temp": current_temp,
                "ramp_time_ms": ramp_ms,
                "rectal_override_target": -1000.0,
                "total_step_time_ms": total_ms,
            })

        if len(steps) > 10:
            raise ValueError("Profile may contain at most 10 steps")

        graph_points = [
            {
                "time": time_min * 60.0,
                "temp": temp_c,
                "actualPlateTarget": temp_c,
            }
            for time_min, temp_c, _ in rows
        ]

        return steps, graph_points

    def _steps_to_graph_points(self, steps):
        cumulative_time = 0.0
        graph_points = []

        for step in steps:
            start_temp = float(step["plate_start_temp"])
            end_temp = float(step["plate_end_temp"])
            total_time_s = float(step["total_step_time_ms"]) / 1000.0
            rectal_target = float(step.get("rectal_override_target", -1000.0))
            has_rectal_target = rectal_target > -999.0

            start_point = {
                "time": cumulative_time,
                "temp": start_temp,
                "actualPlateTarget": start_temp,
            }
            if has_rectal_target:
                start_point["rectalSetpoint"] = rectal_target
            graph_points.append(start_point)

            cumulative_time += total_time_s
            end_point = {
                "time": cumulative_time,
                "temp": end_temp,
                "actualPlateTarget": end_temp,
            }
            if has_rectal_target:
                end_point["rectalSetpoint"] = rectal_target
            graph_points.append(end_point)

        return graph_points

    def request_status(self):
        self.serial_manager.sendCMD("get", "status")

    def trigger_panic(self):
        self.serial_manager.sendCMD("panic", "")
        QMessageBox.critical(self, "PANIC", "🚨 PANIC triggered! Manual intervention required.")

    def clear_failsafe(self):
        self.serial_manager.sendCMD("failsafe_clear", "")
        self.log("🔧 Sent failsafe_clear command to Arduino")

    def save_pid_to_eeprom(self):
        self.serial_manager.sendCMD("save_eeprom", "")
        self.log("💾 PID values saved to EEPROM")

    def set_pid_values(self):
        try:
            kp = float(self.kpInput.text())
            ki = float(self.kiInput.text())
            kd = float(self.kdInput.text())
            self.serial_manager.sendSET("pid_kp", kp)
            self.serial_manager.sendSET("pid_ki", ki)
            self.serial_manager.sendSET("pid_kd", kd)
            self.log(f"✅ Set PID: Kp={kp}, Ki={ki}, Kd={kd}")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for PID parameters.")

    def refresh_ports(self):
        self.portSelector.clear()
        ports = self.serial_manager.list_ports()
        self.portSelector.addItems(ports)

    def toggle_connection(self):
        if self.serial_manager.is_connected():
            self.serial_manager.disconnect()
            self.connectButton.setText("Connect")
            self.connectionStatusLabel.setText("Disconnected")
            self.log("🔌 Disconnected")
        else:
            port = self.portSelector.currentText()
            if self.serial_manager.connect(port):
                self.connectButton.setText("Disconnect")
                self.connectionStatusLabel.setText(f"Connected to {port}")
                self.log(f"🔌 Connected to {port}")
                QTimer.singleShot(500, self.load_config_and_sync)

    def load_config_and_sync(self):
        self.log("Loading config and syncing...")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())