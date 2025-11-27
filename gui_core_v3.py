"""
Musehypothermi GUI v3.0 - WITH ASYMMETRIC PID INTEGRATION
Complete integration showing exactly where to place the new code
"""

import sys
import json
import time
import csv
import os
import traceback
import math
from typing import Dict, List, Optional, Any, Tuple

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel,
    QVBoxLayout, QWidget, QFileDialog, QHBoxLayout,
    QTextEdit, QComboBox, QMessageBox, QGroupBox,
    QFormLayout, QLineEdit, QSplitter,
    QProgressBar, QCheckBox, QSpinBox, QGridLayout,
    QTabWidget, QScrollArea, QFrame, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QStackedWidget,
    QInputDialog, QTableWidget, QTableWidgetItem,
    QListWidget
)
from PySide6.QtCore import QTimer, Qt, Signal, QSignalBlocker
from PySide6.QtGui import QFont, QPalette, QColor, QTextCursor

# Matplotlib imports
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT,
)
from matplotlib.figure import Figure

import pyqtgraph as pg

# Local imports
from framework.serial_comm import SerialManager
from framework.event_logger import EventLogger
from framework.profile_loader import ProfileLoader
from framework.logger import Logger
from profile_graph_widget import _first_present

# ============================================================================
# 1. ADD THIS NEW CLASS BEFORE THE MatplotlibGraphWidget CLASS
# ============================================================================


class MaxOutputDialog(QDialog):
    """Dialog that lets the user edit heating and cooling output limits."""

    def __init__(self, heating: float, cooling: float, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Max Output Limits")
        self.setModal(True)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        self.heating_spin = QDoubleSpinBox()
        self.heating_spin.setRange(0.0, 100.0)
        self.heating_spin.setDecimals(1)
        self.heating_spin.setSingleStep(1.0)
        self.heating_spin.setSuffix(" %")
        self.heating_spin.setValue(max(0.0, heating))

        self.cooling_spin = QDoubleSpinBox()
        self.cooling_spin.setRange(0.0, 100.0)
        self.cooling_spin.setDecimals(1)
        self.cooling_spin.setSingleStep(1.0)
        self.cooling_spin.setSuffix(" %")
        self.cooling_spin.setValue(max(0.0, cooling))

        form.addRow("Heating limit:", self.heating_spin)
        form.addRow("Cooling limit:", self.cooling_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def get_limits(parent: QWidget, heating: float, cooling: float) -> Tuple[float, float, bool]:
        dialog = MaxOutputDialog(heating, cooling, parent)
        accepted = dialog.exec() == QDialog.Accepted
        return dialog.heating_spin.value(), dialog.cooling_spin.value(), accepted


class AsymmetricPIDControls(QWidget):
    """Enhanced controls for asymmetric PID system"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.emergency_event_history = (
            parent.emergency_event_history
            if parent and hasattr(parent, "emergency_event_history")
            else []
        )
        self.emergency_stop_active = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()

        # Mode indicator
        self.mode_indicator = QLabel("REGULATION MODE - HEATING")
        self.mode_indicator.setStyleSheet("""
            QLabel {
                background-color: #ff6b35;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
                text-align: center;
            }
        """)
        self.mode_indicator.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mode_indicator)

        # PID parameter groups
        params_group = QGroupBox("Asymmetric PID Parameters")
        params_layout = QGridLayout()

        cooling_group = QGroupBox("Cooling PID")
        cooling_layout = QGridLayout()
        cooling_layout.setHorizontalSpacing(14)
        cooling_layout.setVerticalSpacing(8)

        self.kp_cooling_input = QLineEdit("0.8")
        self.kp_cooling_input.setMinimumWidth(120)
        self.kp_cooling_input.setPlaceholderText("Enter Kp")
        self.ki_cooling_input = QLineEdit("0.02")
        self.ki_cooling_input.setMinimumWidth(120)
        self.ki_cooling_input.setPlaceholderText("Enter Ki")
        self.kd_cooling_input = QLineEdit("3.0")
        self.kd_cooling_input.setMinimumWidth(120)
        self.kd_cooling_input.setPlaceholderText("Enter Kd")

        cooling_layout.addWidget(QLabel("Kp"), 0, 0)
        cooling_layout.addWidget(self.kp_cooling_input, 0, 1)

        cooling_layout.addWidget(QLabel("Ki"), 1, 0)
        cooling_layout.addWidget(self.ki_cooling_input, 1, 1)

        cooling_layout.addWidget(QLabel("Kd"), 2, 0)
        cooling_layout.addWidget(self.kd_cooling_input, 2, 1)

        self.set_cooling_pid_button = QPushButton("Apply Cooling PID")
        self.set_cooling_pid_button.clicked.connect(self.set_cooling_pid)
        cooling_layout.addWidget(self.set_cooling_pid_button, 3, 0, 1, 3)
        cooling_layout.setColumnStretch(1, 1)

        cooling_group.setLayout(cooling_layout)

        heating_group = QGroupBox("Heating PID")
        heating_layout = QGridLayout()
        heating_layout.setHorizontalSpacing(14)
        heating_layout.setVerticalSpacing(8)

        self.kp_heating_input = QLineEdit("2.5")
        self.kp_heating_input.setMinimumWidth(120)
        self.kp_heating_input.setPlaceholderText("Enter Kp")
        self.ki_heating_input = QLineEdit("0.2")
        self.ki_heating_input.setMinimumWidth(120)
        self.ki_heating_input.setPlaceholderText("Enter Ki")
        self.kd_heating_input = QLineEdit("1.2")
        self.kd_heating_input.setMinimumWidth(120)
        self.kd_heating_input.setPlaceholderText("Enter Kd")

        heating_layout.addWidget(QLabel("Kp"), 0, 0)
        heating_layout.addWidget(self.kp_heating_input, 0, 1)

        heating_layout.addWidget(QLabel("Ki"), 1, 0)
        heating_layout.addWidget(self.ki_heating_input, 1, 1)

        heating_layout.addWidget(QLabel("Kd"), 2, 0)
        heating_layout.addWidget(self.kd_heating_input, 2, 1)

        self.set_heating_pid_button = QPushButton("Apply Heating PID")
        self.set_heating_pid_button.clicked.connect(self.set_heating_pid)
        heating_layout.addWidget(self.set_heating_pid_button, 3, 0, 1, 3)
        heating_layout.setColumnStretch(1, 1)

        heating_group.setLayout(heating_layout)

        params_layout.addWidget(cooling_group, 0, 0)
        params_layout.addWidget(heating_group, 0, 1)
        params_layout.setColumnStretch(0, 1)
        params_layout.setColumnStretch(1, 1)

        button_row = QHBoxLayout()
        self.refresh_pid_button = QPushButton("Refresh From Device")
        self.refresh_pid_button.clicked.connect(self.refresh_pid_from_device)
        self.apply_both_pid_button = QPushButton("Apply Both PID")
        self.apply_both_pid_button.clicked.connect(self.apply_both_pid)

        button_row.addWidget(self.refresh_pid_button)
        button_row.addWidget(self.apply_both_pid_button)
        button_row.addStretch()

        params_layout.addLayout(button_row, 1, 0, 1, 2)
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Safety controls
        safety_group = QGroupBox("Safety Controls")
        safety_layout = QGridLayout()
        safety_layout.setHorizontalSpacing(14)
        safety_layout.setVerticalSpacing(10)

        # Emergency stop
        self.emergency_stop_button = QPushButton("Emergency Stop")
        self.emergency_stop_button.clicked.connect(self.emergency_stop)
        self.emergency_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
            }
        """)
        safety_layout.addWidget(self.emergency_stop_button, 0, 0, 1, 4)

        safety_layout.addWidget(QLabel("Max Temp Change:"), 1, 0)
        self.cooling_rate_input = QLineEdit("1.5")
        self.cooling_rate_input.setMinimumWidth(120)
        self.cooling_rate_input.setPlaceholderText("°C per second")
        safety_layout.addWidget(self.cooling_rate_input, 1, 1)
        safety_layout.addWidget(QLabel("°C/s"), 1, 2)

        self.set_rate_limit_button = QPushButton("Set")
        self.set_rate_limit_button.clicked.connect(self.set_cooling_rate_limit)
        self.set_rate_limit_button.setFixedWidth(60)
        safety_layout.addWidget(self.set_rate_limit_button, 1, 3)

        safety_layout.addWidget(QLabel("Deadband:"), 2, 0)
        self.deadband_input = QLineEdit("0.5")
        self.deadband_input.setMinimumWidth(90)
        safety_layout.addWidget(self.deadband_input, 2, 1)
        safety_layout.addWidget(QLabel("°C"), 2, 2)

        safety_layout.addWidget(QLabel("Safety Margin:"), 3, 0)
        self.safety_margin_input = QLineEdit("1.5")
        self.safety_margin_input.setMinimumWidth(90)
        safety_layout.addWidget(self.safety_margin_input, 3, 1)
        safety_layout.addWidget(QLabel("°C"), 3, 2)

        self.set_safety_params_button = QPushButton("Update")
        self.set_safety_params_button.clicked.connect(self.set_safety_params)
        self.set_safety_params_button.setFixedWidth(80)
        safety_layout.addWidget(self.set_safety_params_button, 3, 3)

        safety_layout.setColumnStretch(1, 1)

        safety_group.setLayout(safety_layout)
        layout.addWidget(safety_group)

        # Status display
        status_group = QGroupBox("System Status")
        status_layout = QGridLayout()

        self.current_mode_label = QLabel("Unknown")
        self.current_mode_label.setStyleSheet("color: #6c757d; font-weight: bold;")
        self.temperature_rate_label = QLabel("0.000 °C/s")
        self.temperature_rate_label.setStyleSheet("color: #28a745; font-weight: bold;")
        self.emergency_status_label = QLabel("✅ Clear")
        self.emergency_status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        
        status_layout.addWidget(QLabel("Current Mode:"), 0, 0)
        status_layout.addWidget(self.current_mode_label, 0, 1)
        
        status_layout.addWidget(QLabel("Temp Rate:"), 1, 0)
        status_layout.addWidget(self.temperature_rate_label, 1, 1)
        
        status_layout.addWidget(QLabel("Emergency:"), 2, 0)
        status_layout.addWidget(self.emergency_status_label, 2, 1)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Emergency events log
        emergency_group = QGroupBox("🚨 Emergency Events")
        emergency_layout = QVBoxLayout()

        emergency_controls = QHBoxLayout()
        self.clearEmergencyLogButton = QPushButton("🧹 Clear log")
        self.clearEmergencyLogButton.clicked.connect(self.clear_emergency_log)
        emergency_controls.addWidget(self.clearEmergencyLogButton)
        emergency_controls.addStretch()

        self.emergencyEventList = QListWidget()
        self.emergencyEventList.setMinimumHeight(120)
        self.emergencyEventList.setMaximumHeight(180)
        self.emergencyEventList.setStyleSheet(
            """
            QListWidget {
                background-color: #fff5f5;
                border: 1px solid #f5c2c7;
                border-radius: 6px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 4px;
            }
            """
        )

        emergency_layout.addLayout(emergency_controls)
        emergency_layout.addWidget(self.emergencyEventList)
        if self.emergency_event_history:
            self.emergencyEventList.addItems(self.emergency_event_history)
            self.emergencyEventList.scrollToBottom()
        emergency_group.setLayout(emergency_layout)
        layout.addWidget(emergency_group)
        self.status_group = status_group
        self.external_mode_label: Optional[QLabel] = None
        self.external_rate_label: Optional[QLabel] = None
        self.external_emergency_label: Optional[QLabel] = None
        
        layout.addStretch()
        self.setLayout(layout)

    def register_status_labels(
        self,
        mode_label: QLabel,
        rate_label: QLabel,
        emergency_label: QLabel,
    ):
        """Expose shared status labels so the main panel can mirror updates."""
        self.external_mode_label = mode_label
        self.external_rate_label = rate_label
        self.external_emergency_label = emergency_label

        # Prime external mirrors with the current values
        if self.current_mode_label and self.external_mode_label:
            self.external_mode_label.setText(self.current_mode_label.text())
            self.external_mode_label.setStyleSheet(self.current_mode_label.styleSheet())
        if self.temperature_rate_label and self.external_rate_label:
            self.external_rate_label.setText(self.temperature_rate_label.text())
            self.external_rate_label.setStyleSheet(self.temperature_rate_label.styleSheet())
        if self.emergency_status_label and self.external_emergency_label:
            self.external_emergency_label.setText(self.emergency_status_label.text())
            self.external_emergency_label.setStyleSheet(self.emergency_status_label.styleSheet())

    def update_status(self, data):
        """Update status displays from Arduino data"""
        try:
            # Update mode indicator
            if "cooling_mode" in data:
                if data["cooling_mode"]:
                    self.mode_indicator.setText("REGULATION MODE - COOLING")
                    self.mode_indicator.setStyleSheet("""
                        QLabel {
                            background-color: #4dabf7;
                            color: white;
                            font-weight: bold;
                            padding: 8px;
                            border-radius: 5px;
                            text-align: center;
                        }
                    """)
                    self._update_label_styles(
                        [self.current_mode_label, self.external_mode_label],
                        "Cooling",
                        "color: #4dabf7; font-weight: bold;",
                    )
                else:
                    self.mode_indicator.setText("REGULATION MODE - HEATING")
                    self.mode_indicator.setStyleSheet("""
                        QLabel {
                            background-color: #ff6b35;
                            color: white;
                            font-weight: bold;
                            padding: 8px;
                            border-radius: 5px;
                            text-align: center;
                        }
                    """)
                    self._update_label_styles(
                        [self.current_mode_label, self.external_mode_label],
                        "Heating",
                        "color: #ff6b35; font-weight: bold;",
                    )

            # Update temperature rate
            if "temperature_rate" in data:
                rate = float(data["temperature_rate"])
                style = "color: #28a745; font-weight: bold;"

                # Color code based on rate
                if rate < -1.0:  # Fast cooling
                    style = "color: #dc3545; font-weight: bold;"
                elif rate < -0.5:  # Moderate cooling
                    style = "color: #fd7e14; font-weight: bold;"
                elif rate > 0.5:  # Heating
                    style = "color: #ff6b35; font-weight: bold;"

                self._update_label_styles(
                    [self.temperature_rate_label, self.external_rate_label],
                    f"{rate:.3f} °C/s",
                    style,
                )

            # Update emergency status
            if "emergency_stop" in data:
                emergency_active = bool(data["emergency_stop"])
                state_changed = emergency_active != self.emergency_stop_active

                if emergency_active:
                    self._update_label_styles(
                        [self.emergency_status_label, self.external_emergency_label],
                        "🚨 ACTIVE",
                        "color: #dc3545; font-weight: bold;",
                    )
                    if state_changed:
                        if self.event_logger is not None:
                            self.event_logger.log_event("EVENT: EMERGENCY_STOP_TRIGGERED")
                        if self.data_logger is not None:
                            self.data_logger.log_event("EMERGENCY_STOP_TRIGGERED")
                        self.log("🚨 Emergency stop active", "error")
                        self.log_emergency_event("EMERGENCY STOP TRIGGERED")
                else:
                    self._update_label_styles(
                        [self.emergency_status_label, self.external_emergency_label],
                        "✅ Clear",
                        "color: #28a745; font-weight: bold;",
                    )
                    if state_changed:
                        if self.event_logger is not None:
                            self.event_logger.log_event("EVENT: EMERGENCY_STOP_CLEARED")
                        if self.data_logger is not None:
                            self.data_logger.log_event("EMERGENCY_STOP_CLEARED")
                        self.log("✅ Emergency stop cleared", "info")
                        self.log_emergency_event("EMERGENCY STOP CLEARED")

                self.emergency_stop_active = emergency_active
            
            # Sync parameter fields when not being edited
            if all(key in data for key in ["pid_cooling_kp", "pid_cooling_ki", "pid_cooling_kd"]):
                if not self.kp_cooling_input.hasFocus():
                    self.kp_cooling_input.setText(f"{float(data['pid_cooling_kp']):.3f}")
                if not self.ki_cooling_input.hasFocus():
                    self.ki_cooling_input.setText(f"{float(data['pid_cooling_ki']):.4f}")
                if not self.kd_cooling_input.hasFocus():
                    self.kd_cooling_input.setText(f"{float(data['pid_cooling_kd']):.3f}")

            if all(key in data for key in ["pid_heating_kp", "pid_heating_ki", "pid_heating_kd"]):
                if not self.kp_heating_input.hasFocus():
                    self.kp_heating_input.setText(f"{float(data['pid_heating_kp']):.3f}")
                if not self.ki_heating_input.hasFocus():
                    self.ki_heating_input.setText(f"{float(data['pid_heating_ki']):.3f}")
                if not self.kd_heating_input.hasFocus():
                    self.kd_heating_input.setText(f"{float(data['pid_heating_kd']):.3f}")

            if "cooling_rate_limit" in data and not self.cooling_rate_input.hasFocus():
                self.cooling_rate_input.setText(f"{float(data['cooling_rate_limit']):.2f}")

            if "deadband" in data and not self.deadband_input.hasFocus():
                self.deadband_input.setText(f"{float(data['deadband']):.2f}")

            if "safety_margin" in data and not self.safety_margin_input.hasFocus():
                self.safety_margin_input.setText(f"{float(data['safety_margin']):.2f}")

        except Exception as e:
            print(f"Status update error: {e}")

    @staticmethod
    def _update_label_styles(labels: List[Optional[QLabel]], text: str, style: str):
        for label in labels:
            if label is not None:
                label.setText(text)
                label.setStyleSheet(style)
    
    def set_cooling_pid(self):
        """Send cooling PID parameters to the controller."""
        try:
            kp = float(self.kp_cooling_input.text())
            ki = float(self.ki_cooling_input.text())
            kd = float(self.kd_cooling_input.text())

            if self.parent.send_asymmetric_command("set_cooling_pid", {"kp": kp, "ki": ki, "kd": kd}):
                self.parent.log(f"❄️ Cooling PID set: Kp={kp:.3f}, Ki={ki:.4f}, Kd={kd:.3f}", "success")

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Cooling PID error: {e}")
            self.parent.log(f"❌ Invalid cooling PID: {e}", "error")
    
    def set_heating_pid(self):
        """Send heating PID parameters to the controller."""
        try:
            kp = float(self.kp_heating_input.text())
            ki = float(self.ki_heating_input.text())
            kd = float(self.kd_heating_input.text())

            if self.parent.send_asymmetric_command("set_heating_pid", {"kp": kp, "ki": ki, "kd": kd}):
                self.parent.log(f"Heating PID set: Kp={kp:.3f}, Ki={ki:.4f}, Kd={kd:.3f}", "success")

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Heating PID error: {e}")
            self.parent.log(f"❌ Invalid heating PID: {e}", "error")

    def apply_both_pid(self):
        """Apply both cooling and heating PID parameters"""
        try:
            # Cooling values
            cool_kp = float(self.kp_cooling_input.text())
            cool_ki = float(self.ki_cooling_input.text())
            cool_kd = float(self.kd_cooling_input.text())

            # Heating values
            heat_kp = float(self.kp_heating_input.text())
            heat_ki = float(self.ki_heating_input.text())
            heat_kd = float(self.kd_heating_input.text())

            ok_cool = self.parent.send_asymmetric_command(
                "set_cooling_pid", {"kp": cool_kp, "ki": cool_ki, "kd": cool_kd}
            )
            ok_heat = self.parent.send_asymmetric_command(
                "set_heating_pid", {"kp": heat_kp, "ki": heat_ki, "kd": heat_kd}
            )

            if ok_cool and ok_heat:
                self.parent.log(
                    (
                        "Applied asymmetric PID → "
                        f"Cool[Kp={cool_kp:.3f}, Ki={cool_ki:.4f}, Kd={cool_kd:.3f}] | "
                        f"Heat[Kp={heat_kp:.3f}, Ki={heat_ki:.4f}, Kd={heat_kd:.3f}]"
                    ),
                    "success",
                )

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))
            self.parent.log(f"❌ PID input error: {e}", "error")

    def refresh_pid_from_device(self):
        """Request PID parameters from device"""
        self.parent.refresh_pid_from_device()

    def emergency_stop(self):
        """Trigger emergency stop"""
        reply = QMessageBox.critical(
            self, "🚨 EMERGENCY STOP",
            "EMERGENCY STOP will immediately halt all cooling/heating!\n\nConfirm emergency stop?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            if self.parent.send_asymmetric_command("emergency_stop", {"enabled": True}):
                self.parent.log("🚨 EMERGENCY STOP ACTIVATED!", "error")

    def set_cooling_rate_limit(self):
        """Set maximum cooling rate"""
        try:
            rate = float(self.cooling_rate_input.text())
            if not (0.1 <= rate <= 3.0):
                raise ValueError("Cooling rate must be 0.1-3.0 °C/s")

            if self.parent.send_asymmetric_command("set_cooling_rate_limit", {"rate": rate}):
                self.parent.log(f"Cooling rate limit: {rate:.1f} °C/s", "command")

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Rate limit error: {e}")

    def set_safety_params(self):
        """Set safety deadband and margin"""
        try:
            deadband = float(self.deadband_input.text())
            margin = float(self.safety_margin_input.text())
            if not (0.1 <= deadband <= 5.0):
                raise ValueError("Deadband must be 0.1-5.0 °C")
            if not (0.5 <= margin <= 3.0):
                raise ValueError("Safety margin must be 0.5-3.0 °C")

            if self.parent.send_asymmetric_command(
                "set_safety_margin", {"margin": margin, "deadband": deadband}
            ):
                self.parent.log(
                    f"Safety limits: deadband {deadband:.1f} °C, margin {margin:.1f} °C",
                    "command",
                )

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Safety margin error: {e}")

    def clear_emergency_log(self):
        """Clear emergency log via parent handler so UI stays in sync."""

        if self.parent and hasattr(self.parent, "clear_emergency_log"):
            self.parent.clear_emergency_log()
        else:
            self.emergency_event_history.clear()
            if hasattr(self, "emergencyEventList"):
                self.emergencyEventList.clear()

# ============================================================================
# Autotune wizard implementation
# ============================================================================

class AutotuneDataAnalyzer:
    """Collect samples and compute Ziegler-Nichols inspired PID values."""

    MIN_SAMPLES = 40
    STABLE_WINDOW = 25

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.start_timestamp: Optional[float] = None
        self.timestamps: List[float] = []
        self.temperatures: List[float] = []
        self.outputs: List[float] = []

    def add_sample(self, timestamp: float, temperature: float, output: float) -> None:
        if self.start_timestamp is None:
            self.start_timestamp = timestamp

        elapsed = max(0.0, timestamp - self.start_timestamp)
        self.timestamps.append(elapsed)
        self.temperatures.append(temperature)
        self.outputs.append(output)

    def has_enough_samples(self) -> bool:
        return len(self.timestamps) >= self.MIN_SAMPLES

    def is_stable(self, tolerance: float = 0.05) -> bool:
        if len(self.temperatures) < self.STABLE_WINDOW:
            return False

        recent = self.temperatures[-self.STABLE_WINDOW:]
        if not recent:
            return False

        return (max(recent) - min(recent)) <= tolerance

    def max_rate(self) -> float:
        if len(self.timestamps) < 2:
            return 0.0

        max_rate = 0.0
        for idx in range(1, len(self.timestamps)):
            dt = self.timestamps[idx] - self.timestamps[idx - 1]
            if dt <= 0:
                continue
            rate = (self.temperatures[idx] - self.temperatures[idx - 1]) / dt
            if rate > max_rate:
                max_rate = rate
        return max_rate

    @staticmethod
    def _moving_average(values: List[float], window: int = 10) -> float:
        if not values:
            return 0.0
        if len(values) < window:
            return sum(values) / len(values)
        return sum(values[-window:]) / float(window)

    def _estimate_dead_time(self, start_temp: float, final_temp: float) -> float:
        if not self.timestamps:
            return 0.0

        delta = final_temp - start_temp
        if abs(delta) < 1e-6:
            return 0.0

        threshold = start_temp + 0.05 * delta
        for t, temp in zip(self.timestamps, self.temperatures):
            if (delta > 0 and temp >= threshold) or (delta < 0 and temp <= threshold):
                return max(0.0, t)
        return 0.0

    def _estimate_time_constant(self, start_temp: float, final_temp: float) -> float:
        if not self.timestamps:
            return 0.0

        delta = final_temp - start_temp
        if abs(delta) < 1e-6:
            return 0.0

        target = start_temp + 0.63 * delta
        for t, temp in zip(self.timestamps, self.temperatures):
            if (delta > 0 and temp >= target) or (delta < 0 and temp <= target):
                return max(0.0, t)
        return self.timestamps[-1]

    def _estimate_settling_time(self, final_temp: float, tolerance: float = 0.1) -> float:
        if not self.timestamps:
            return 0.0

        for idx in range(len(self.timestamps) - 1, -1, -1):
            window = self.temperatures[idx:]
            if not window:
                continue
            if max(abs(val - final_temp) for val in window) <= tolerance:
                return self.timestamps[idx]
        return self.timestamps[-1]

    def compute_results(self) -> Optional[Dict[str, float]]:
        if not self.has_enough_samples():
            return None

        initial_temp = self.temperatures[0]
        final_temp = self._moving_average(self.temperatures, 10)
        delta_temp = final_temp - initial_temp
        if abs(delta_temp) < 0.05:
            return None

        initial_output = self._moving_average(self.outputs, 12)
        final_output = self._moving_average(self.outputs, 4)
        output_span = max(self.outputs) - min(self.outputs)
        if abs(output_span) < 1.0:
            output_span = final_output - initial_output

        if abs(output_span) < 1e-3:
            return None

        step_fraction = output_span / 100.0
        process_gain = delta_temp / step_fraction if step_fraction else 0.0

        dead_time = self._estimate_dead_time(initial_temp, final_temp)
        t63 = self._estimate_time_constant(initial_temp, final_temp)
        time_constant = max(0.1, t63 - dead_time)

        duration = self.timestamps[-1] if self.timestamps else 0.0
        sample_count = len(self.timestamps)

        kp = 0.0
        ki = 0.0
        kd = 0.0
        if process_gain != 0 and dead_time > 0:
            kp = 1.2 * time_constant / (process_gain * dead_time)
            ki = kp / (2.0 * dead_time)
            kd = kp * dead_time * 0.5

        overshoot = max(self.temperatures) - final_temp
        max_rate = self.max_rate()
        settling_time = self._estimate_settling_time(final_temp)

        return {
            "kp": kp,
            "ki": ki,
            "kd": kd,
            "process_gain": process_gain,
            "dead_time": dead_time,
            "time_constant": time_constant,
            "delta_temp": delta_temp,
            "overshoot": overshoot,
            "max_rate": max_rate,
            "settling_time": settling_time,
            "initial_temp": initial_temp,
            "final_temp": final_temp,
            "output_span": output_span,
            "duration": duration,
            "sample_count": sample_count,
        }


class AutotuneWizardTab(QWidget):
    """Guided autotune workflow with live analysis and UI."""

    HEATING_LIMITS = {
        "kp": (0.5, 5.0),
        "ki": (0.05, 1.0),
        "kd": (0.1, 3.0),
    }
    COOLING_LIMITS = {
        "kp": (0.1, 2.0),
        "ki": (0.01, 0.1),
        "kd": (0.5, 5.0),
    }

    PERCENT_PER_DEGREE = 4.0
    MIN_STEP_PERCENT = 5.0
    MANUAL_STEP_SAFETY_FRACTION = 0.85

    RESULT_FLOAT_FIELDS = (
        "kp",
        "ki",
        "kd",
        "heating_process_gain",
        "heating_dead_time",
        "heating_time_constant",
        "heating_delta_temp",
        "heating_max_rate",
        "heating_overshoot",
        "heating_duration",
        "heating_step_percent",
        "cooling_process_gain",
        "cooling_dead_time",
        "cooling_time_constant",
        "cooling_delta_temp",
        "cooling_max_rate",
        "cooling_overshoot",
        "cooling_duration",
        "cooling_step_percent",
        "cooling_kp",
        "cooling_ki",
        "cooling_kd",
        "duration",
        "baseline_temp",
        "target_delta",
    )
    RESULT_INT_FIELDS = (
        "sample_count",
        "heating_sample_count",
        "cooling_sample_count",
    )

    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.parent = parent
        self.analyzer = AutotuneDataAnalyzer()
        self.collecting = False
        self._last_plot_update = 0.0
        self._canvas: Optional[FigureCanvas] = None
        self._axes_temp = None
        self._axes_output = None
        self._result_axes = None
        self._result_canvas: Optional[FigureCanvas] = None
        self._original_target: Optional[float] = None
        self._autotune_command_sent = False
        self._percent_user_override = False
        self._updating_percent_spin = False
        self._latest_results_payload: Dict[str, Any] = {}
        self._latest_cooling_pid: Tuple[Optional[float], Optional[float], Optional[float]] = (
            None,
            None,
            None,
        )
        self._expected_delta: Optional[float] = None
        self._commanded_step_percent: Optional[float] = None
        self._reported_step_clamp = False
        self._commanded_direction: Optional[str] = None

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        intro = self._build_intro_page()
        collect = self._build_collect_page()
        results = self._build_results_page()

        self.stack.addWidget(intro)
        self.stack.addWidget(collect)
        self.stack.addWidget(results)

    def _build_intro_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setSpacing(18)

        title = QLabel("Autotune wizard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        vbox.addWidget(title)

        description = QLabel(
            "Denne wizzarden analyserer systemresponsen og foreslår nye PID-verdier.\n"
            "• Kontrolleren kjører et manuelt varme-steg mens wizzarden logger reaksjonen.\n"
            "• Sørg for at systemet er stabilt før start, og velg ønsket retning.\n"
            "• Trykk start for å sende autotune-kommando til kontrolleren.\n"
            "• Følg grafene til systemet stabiliserer seg.\n"
            "• Evaluer verdiene og aktiver dem når du er fornøyd."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #495057;")
        vbox.addWidget(description)

        config_group = QGroupBox("Oppsett for stegtest")
        config_layout = QFormLayout()

        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.5, 15.0)
        self.step_spin.setDecimals(1)
        self.step_spin.setSingleStep(0.5)
        self.step_spin.setSuffix(" °C")
        self.step_spin.setValue(3.0)
        self.step_spin.valueChanged.connect(self._handle_step_changed)
        config_layout.addRow("Stegstørrelse:", self.step_spin)

        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Varme (øke mål)", "heating")
        self.direction_combo.addItem("Kjøling (senke mål)", "cooling")
        self.direction_combo.currentIndexChanged.connect(self._handle_direction_changed)
        config_layout.addRow("Retning:", self.direction_combo)

        self.step_percent_spin = QDoubleSpinBox()
        self.step_percent_spin.setRange(0.0, 100.0)
        self.step_percent_spin.setDecimals(1)
        self.step_percent_spin.setSingleStep(0.5)
        self.step_percent_spin.setSuffix(" %")
        step_limits = self._recommended_step_percent(self.step_spin.value(), "heating")
        self.step_percent_spin.setValue(step_limits["recommended"])
        self.step_percent_spin.valueChanged.connect(self._handle_percent_changed)
        config_layout.addRow("Manuelt pådrag:", self.step_percent_spin)

        self.percent_hint_label = QLabel()
        self.percent_hint_label.setWordWrap(True)
        self.percent_hint_label.setStyleSheet("color: #495057; font-size: 11px;")
        config_layout.addRow("Forklaring:", self.percent_hint_label)

        config_group.setLayout(config_layout)
        vbox.addWidget(config_group)

        self._update_percent_hint(self.step_percent_spin.value(), step_limits)

        self.start_button = QPushButton("Start autotune")
        self.start_button.setStyleSheet(
            "background-color: #28a745; color: white; font-weight: bold; padding: 8px 24px;"
        )
        self.start_button.clicked.connect(self.start_sequence)
        self.start_button.setCursor(Qt.PointingHandCursor)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.start_button)
        button_row.addStretch()
        vbox.addLayout(button_row)

        info = QLabel(
            "Tips: La systemet stabilisere seg nær målet før du starter. Stegstørrelsen brukes til å lage en Ziegler-Nichols stegrespons."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background: #f8f9fa; border: 1px solid #dee2e6; padding: 12px; border-radius: 6px;")
        vbox.addWidget(info)

        vbox.addStretch(1)
        return page

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            coerced = float(value)
            if math.isnan(coerced):
                return None
            return coerced
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_number(value: Optional[float], decimals: int) -> str:
        if value is None:
            return "–"
        return f"{value:.{decimals}f}"

    @staticmethod
    def _format_int(value: Optional[int]) -> str:
        if value is None:
            return "–"
        return str(value)

    def _normalize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}

        heating = results.get("heating") if isinstance(results.get("heating"), dict) else {}
        cooling = results.get("cooling") if isinstance(results.get("cooling"), dict) else {}
        meta = results.get("meta") if isinstance(results.get("meta"), dict) else {}

        normalized["kp"] = self._coerce_float(results.get("kp", heating.get("kp")))
        normalized["ki"] = self._coerce_float(results.get("ki", heating.get("ki")))
        normalized["kd"] = self._coerce_float(results.get("kd", heating.get("kd")))

        normalized["heating_process_gain"] = self._coerce_float(heating.get("process_gain"))
        normalized["heating_dead_time"] = self._coerce_float(heating.get("dead_time"))
        normalized["heating_time_constant"] = self._coerce_float(heating.get("time_constant"))
        normalized["heating_delta_temp"] = self._coerce_float(heating.get("delta_temp"))
        normalized["heating_max_rate"] = self._coerce_float(heating.get("max_rate"))
        normalized["heating_overshoot"] = self._coerce_float(heating.get("overshoot"))
        normalized["heating_duration"] = self._coerce_float(heating.get("duration"))
        normalized["heating_step_percent"] = self._coerce_float(
            heating.get("step_percent", meta.get("heating_step_percent"))
        )
        normalized["heating_sample_count"] = self._coerce_int(heating.get("sample_count"))
        normalized["heating_available"] = bool(heating.get("available", bool(heating)))
        if isinstance(heating.get("reason"), str):
            normalized["heating_reason"] = heating.get("reason")
        else:
            normalized["heating_reason"] = None

        normalized["cooling_process_gain"] = self._coerce_float(cooling.get("process_gain"))
        normalized["cooling_dead_time"] = self._coerce_float(cooling.get("dead_time"))
        normalized["cooling_time_constant"] = self._coerce_float(cooling.get("time_constant"))
        normalized["cooling_delta_temp"] = self._coerce_float(cooling.get("delta_temp"))
        normalized["cooling_max_rate"] = self._coerce_float(cooling.get("max_rate"))
        normalized["cooling_overshoot"] = self._coerce_float(cooling.get("overshoot"))
        normalized["cooling_duration"] = self._coerce_float(cooling.get("duration"))
        normalized["cooling_step_percent"] = self._coerce_float(
            cooling.get("step_percent", meta.get("cooling_step_percent"))
        )
        normalized["cooling_kp"] = self._coerce_float(cooling.get("kp"))
        normalized["cooling_ki"] = self._coerce_float(cooling.get("ki"))
        normalized["cooling_kd"] = self._coerce_float(cooling.get("kd"))
        normalized["cooling_sample_count"] = self._coerce_int(cooling.get("sample_count"))
        normalized["cooling_available"] = bool(cooling.get("available", bool(cooling)))
        if isinstance(cooling.get("reason"), str):
            normalized["cooling_reason"] = cooling.get("reason")
        else:
            normalized["cooling_reason"] = None

        normalized["duration"] = self._coerce_float(meta.get("duration", results.get("duration")))
        normalized["sample_count"] = self._coerce_int(meta.get("sample_count", results.get("sample_count")))
        normalized["baseline_temp"] = self._coerce_float(meta.get("baseline_temp"))
        normalized["target_delta"] = self._coerce_float(meta.get("target_delta"))
        normalized["primary_direction"] = (
            meta.get("primary_direction") if isinstance(meta.get("primary_direction"), str) else None
        )
        normalized["autotune_mode"] = self._coerce_int(meta.get("mode"))

        # Backwards-compatible aliases for legacy consumers
        normalized["delta_temp"] = normalized["heating_delta_temp"]
        normalized["max_rate"] = normalized["heating_max_rate"]
        normalized["overshoot"] = normalized["heating_overshoot"]
        normalized["process_gain"] = normalized["heating_process_gain"]

        extras = {}
        for key, value in results.items():
            if key in {"kp", "ki", "kd", "heating", "cooling", "meta"}:
                continue
            extras[key] = value

        normalized["extras"] = extras
        return normalized

    def _build_collect_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        header = QLabel("Steg 2 – måling av respons")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        self.collect_status = QLabel("Venter på respons...")
        self.collect_status.setStyleSheet("color: #17a2b8; font-weight: bold;")
        layout.addWidget(self.collect_status)

        self.metric_label = QLabel("ΔT: –  |  Hastighet: –  |  Overshoot: –")
        self.metric_label.setStyleSheet("color: #495057;")
        layout.addWidget(self.metric_label)

        figure = Figure(figsize=(6, 4))
        self._canvas = FigureCanvas(figure)
        self._axes_temp = figure.add_subplot(211)
        self._axes_output = figure.add_subplot(212, sharex=self._axes_temp)
        self._axes_temp.set_ylabel("Temp [°C]")
        self._axes_output.set_ylabel("PID [%]")
        self._axes_output.set_xlabel("Tid [s]")
        self._axes_temp.grid(True, alpha=0.3)
        self._axes_output.grid(True, alpha=0.3)
        layout.addWidget(self._canvas)

        buttons = QHBoxLayout()
        self.abort_button = QPushButton("Avbryt")
        self.abort_button.setStyleSheet("background-color: #dc3545; color: white;")
        self.abort_button.clicked.connect(self.abort_sequence)

        self.finish_button = QPushButton("Analyser nå")
        self.finish_button.setStyleSheet("background-color: #007bff; color: white;")
        self.finish_button.setEnabled(False)
        self.finish_button.clicked.connect(self.complete_measurement)

        buttons.addStretch()
        buttons.addWidget(self.abort_button)
        buttons.addWidget(self.finish_button)
        layout.addLayout(buttons)

        hint = QLabel("Wizzarden stopper automatisk når temperaturen er stabil i 25 målepunkter (±0.05 °C).")
        hint.setStyleSheet("color: #6c757d; font-size: 11px;")
        layout.addWidget(hint)

        return page

    def _build_results_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        header = QLabel("Steg 3 – foreslåtte PID-verdier")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        self.results_summary = QLabel("Ingen resultater enda")
        self.results_summary.setWordWrap(True)
        self.results_summary.setStyleSheet(
            "background: #f1f3f5; border: 1px solid #dee2e6; padding: 12px; border-radius: 6px;"
        )
        layout.addWidget(self.results_summary)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(-1000000.0, 1000000.0)
        self.kp_spin.setDecimals(3)
        self.kp_spin.setSingleStep(0.05)

        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(-1000000.0, 1000000.0)
        self.ki_spin.setDecimals(4)
        self.ki_spin.setSingleStep(0.01)

        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(-1000000.0, 1000000.0)
        self.kd_spin.setDecimals(3)
        self.kd_spin.setSingleStep(0.05)

        form.addRow("Kp (varme):", self.kp_spin)
        form.addRow("Ki (varme):", self.ki_spin)
        form.addRow("Kd (varme):", self.kd_spin)
        layout.addLayout(form)

        explanation = QLabel(
            "Justeringstips:\n"
            "• Høyere Kp gir raskere respons, men mer overshoot.\n"
            "• Høyere Ki fjerner steady-state-feil, men kan gi oscillasjoner.\n"
            "• Høyere Kd demper overshoot og stabiliserer responsen."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #495057;")
        layout.addWidget(explanation)

        self.limit_notice = QLabel("")
        self.limit_notice.setWordWrap(True)
        self.limit_notice.setStyleSheet("color: #d39e00; font-style: italic;")
        self.limit_notice.hide()
        layout.addWidget(self.limit_notice)

        buttons = QHBoxLayout()
        self.apply_button = QPushButton("Aktiver varme-PID")
        self.apply_button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.apply_button.clicked.connect(self.apply_to_heating)

        self.apply_cooling_button = QPushButton("Aktiver kjøle-PID")
        self.apply_cooling_button.setStyleSheet("background-color: #20c997; color: white; font-weight: bold;")
        self.apply_cooling_button.clicked.connect(self.apply_to_cooling)

        self.apply_both_button = QPushButton("Aktiver begge")
        self.apply_both_button.setStyleSheet("background-color: #6f42c1; color: white; font-weight: bold;")
        self.apply_both_button.clicked.connect(self.apply_to_both)

        self.restart_button = QPushButton("Kjør på nytt")
        self.restart_button.clicked.connect(self.reset_wizard)

        buttons.addStretch()
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.apply_cooling_button)
        buttons.addWidget(self.apply_both_button)
        buttons.addWidget(self.restart_button)
        layout.addLayout(buttons)

        result_canvas = FigureCanvas(Figure(figsize=(6, 3)))
        self._result_canvas = result_canvas
        self._result_axes = result_canvas.figure.add_subplot(111)
        self._result_axes.set_title("Temperaturrespons")
        self._result_axes.set_xlabel("Tid [s]")
        self._result_axes.set_ylabel("Temp [°C]")
        self._result_axes.grid(True, alpha=0.3)
        layout.addWidget(result_canvas)

        return page

    def start_sequence(self) -> None:
        if not self.parent.connection_established:
            QMessageBox.warning(self, "Ikke tilkoblet", "Koble til kontrolleren før du starter autotune.")
            return

        self.analyzer.reset()
        self.collecting = True
        self._last_plot_update = 0.0
        self._clear_plots()
        self.collect_status.setText("Forbereder firmware-autotune...")
        self.collect_status.setStyleSheet("color: #17a2b8; font-weight: bold;")
        self.metric_label.setText("ΔT: –  |  Hastighet: –  |  Overshoot: –")
        self.finish_button.setEnabled(False)
        self.stack.setCurrentIndex(1)
        self._autotune_command_sent = False
        self._latest_cooling_pid = (None, None, None)

        latest_data = getattr(self.parent, "last_status_data", {}) or {}
        autotune_active = bool(latest_data.get("asymmetric_autotune_active")) or bool(
            latest_data.get("autotune_active")
        )

        if autotune_active:
            self.collecting = False
            self._original_target = None
            self._autotune_command_sent = True
            self._clear_plots()
            self.collect_status.setText("Firmware-autotune kjører – venter på resultater...")
            self.collect_status.setStyleSheet("color: #17a2b8; font-weight: bold;")
            self.metric_label.setText("Resultater vises når kontrolleren er ferdig.")
            self.finish_button.setEnabled(False)
            self.parent.log(
                "🎯 Autotune-wizard følger firmware-autotune – avvent resultater fra kontrolleren.",
                "info",
            )
            return

        plate_temp = self.parent.current_plate_temp
        if plate_temp is None:
            plate_temp = float(latest_data.get("cooling_plate_temp", float("nan")))

        target_temp = self.parent.current_target_temp
        if target_temp is None:
            target_temp = float(latest_data.get("plate_target_active", float("nan")))

        if plate_temp is None or math.isnan(plate_temp):
            QMessageBox.warning(self, "Ingen data", "Ingen temperaturdata er tilgjengelig ennå. Vent på statusoppdatering før du starter.")
            self.collecting = False
            self.stack.setCurrentIndex(0)
            return

        if target_temp is None or math.isnan(target_temp):
            target_temp = plate_temp

        self._original_target = target_temp
        direction = str(self.direction_combo.currentData() or "heating")
        direction_label = "varme" if direction == "heating" else "kjøle"
        step = self.step_spin.value()

        requested_percent = float(self.step_percent_spin.value())
        limits = self._recommended_step_percent(step, direction)
        device_cap = limits.get("device_cap", 0.0) or 0.0
        safety_cap = limits.get("safety_cap", 0.0) or 0.0

        tolerance = 0.1
        step_percent = max(0.0, min(requested_percent, 100.0))
        adjustments: List[str] = []

        if step_percent != requested_percent:
            adjustments.append(
                f"begrenset til {step_percent:.1f}% (tillat område 0–100 %)"
            )

        if device_cap <= 0.0 and step_percent < self.MIN_STEP_PERCENT:
            step_percent = self.MIN_STEP_PERCENT
            adjustments.append(
                f"hevet til minimumsanbefalingen {self.MIN_STEP_PERCENT:.1f}%"
            )

        exceeds_device = device_cap > 0.0 and step_percent > device_cap + tolerance
        if exceeds_device:
            if self._percent_user_override:
                self.parent.log(
                    (
                        "ℹ️ Du har valgt et autotune-pådrag på "
                        f"{step_percent:.1f}% {direction_label} som overstiger kontrollergrensen "
                        f"({device_cap:.1f} %). Kontrolleren kan klippe verdien."
                    ),
                    "info",
                )
            else:
                step_percent = device_cap
                adjustments.append(f"klippet til kontrollergrensen {device_cap:.1f}%")

        if safety_cap > 0.0 and step_percent > safety_cap + tolerance:
            self.parent.log(
                (
                    f"ℹ️ Valgt autotune-pådrag {step_percent:.1f}% {direction_label} overstiger anbefalt sikkerhetsnivå "
                    f"({safety_cap:.1f} %). Kontroller at systemet tåler dette steget."
                ),
                "info",
            )

        if adjustments:
            self.parent.log(
                (
                    "⚠️ Autotune-pådrag justert: "
                    + "; ".join(adjustments)
                    + f" (valgt {requested_percent:.1f} %)."
                ),
                "warning",
            )
            self._updating_percent_spin = True
            with QSignalBlocker(self.step_percent_spin):
                self.step_percent_spin.setValue(step_percent)
            self._updating_percent_spin = False
            self._percent_user_override = True
        elif safety_cap > 0.0 and step_percent > safety_cap + tolerance:
            self.parent.log(
                (
                    f"ℹ️ Valgt autotune-pådrag {step_percent:.1f}% overstiger anbefalt sikkerhetsnivå "
                    f"({safety_cap:.1f} %). Kontroller at systemet tåler dette steget."
                ),
                "info",
            )

        self._update_percent_hint(self.step_percent_spin.value(), limits)

        payload = {
            "direction": direction,
            "step_percent": step_percent,
            "target_delta": step,
        }
        if not self.parent.send_asymmetric_command("start_asymmetric_autotune", payload):
            QMessageBox.warning(
                self,
                "Kunne ikke starte",
                "Kontrolleren avviste autotune-kommandoen.",
            )
            self.collecting = False
            self.stack.setCurrentIndex(0)
            return

        self._autotune_command_sent = True
        self._commanded_step_percent = step_percent
        self._reported_step_clamp = False
        self._commanded_direction = direction
        self._expected_delta = step if direction == "heating" else -abs(step)
        self.collect_status.setText(
            f"Firmware-autotune kjører – {step_percent:.1f}% {direction_label}effekt"
        )
        self.metric_label.setText("Samler data – vent til responsen stabiliserer seg.")
        self.parent.log(
            f"🎯 Firmware-autotune startet: {step:.2f} °C steg → {step_percent:.1f}% {direction_label}",
            "info",
        )
        self.parent.request_status()

    def abort_sequence(self) -> None:
        if self.collecting:
            self.parent.log("⛔ Autotune wizard avbrutt", "warning")
        self.collecting = False
        if self._autotune_command_sent:
            if self.parent.send_asymmetric_command("abort_asymmetric_autotune", {}):
                self.parent.log("⛔ Firmware-autotune avbrutt fra wizard", "warning")
        self._autotune_command_sent = False
        self._expected_delta = None
        self._commanded_step_percent = None
        self._commanded_direction = None
        self._reported_step_clamp = False
        self._restore_original_target()
        self._latest_cooling_pid = (None, None, None)
        self.stack.setCurrentIndex(0)

    def complete_measurement(self) -> None:
        results = self.analyzer.compute_results()
        if not results:
            QMessageBox.information(
                self,
                "Manglende data",
                "Wizzarden trenger mer variert data før analysen kan fullføres.",
            )
            return

        self.collecting = False
        self._present_results(results)

    def reset_wizard(self) -> None:
        self.stack.setCurrentIndex(0)
        self.collecting = False
        self._autotune_command_sent = False
        self._expected_delta = None
        self._commanded_step_percent = None
        self._reported_step_clamp = False
        self._restore_original_target()
        self._percent_user_override = False
        self._handle_step_changed(self.step_spin.value())

    def _sanitize_pid_values(
        self, kp: float, ki: float, kd: float, limits: Dict[str, Tuple[float, float]]
    ) -> Tuple[float, float, float, List[str]]:
        adjustments: List[str] = []

        def _clamp(value: float, lower: float, upper: float, label: str) -> float:
            nonlocal adjustments
            clamped = min(max(value, lower), upper)
            if abs(clamped - value) > 1e-6:
                adjustments.append(f"{label}→[{lower}, {upper}]")
            return clamped

        kp_val = _clamp(kp, *limits["kp"], label="Kp")
        ki_val = _clamp(ki, *limits["ki"], label="Ki")
        kd_val = _clamp(kd, *limits["kd"], label="Kd")
        return kp_val, ki_val, kd_val, adjustments

    def _sanitize_heating_values(self, kp: float, ki: float, kd: float) -> Tuple[float, float, float, List[str]]:
        return self._sanitize_pid_values(kp, ki, kd, self.HEATING_LIMITS)

    def _sanitize_cooling_values(self, kp: float, ki: float, kd: float) -> Tuple[float, float, float, List[str]]:
        return self._sanitize_pid_values(kp, ki, kd, self.COOLING_LIMITS)

    def apply_to_heating(self) -> None:
        kp = self.kp_spin.value()
        ki = self.ki_spin.value()
        kd = self.kd_spin.value()
        kp, ki, kd, heat_adj = self._sanitize_heating_values(kp, ki, kd)
        self._update_limit_notice(heat_adj)
        self.kp_spin.setValue(kp)
        self.ki_spin.setValue(ki)
        self.kd_spin.setValue(kd)
        if heat_adj:
            self.parent.log(
                "⚠️ Autotune-verdier klippet til sikre grenser (varme): " + ", ".join(heat_adj),
                "warning",
            )
        self.parent.asymmetric_controls.kp_heating_input.setText(f"{kp:.3f}")
        self.parent.asymmetric_controls.ki_heating_input.setText(f"{ki:.4f}")
        self.parent.asymmetric_controls.kd_heating_input.setText(f"{kd:.3f}")
        self.parent.asymmetric_controls.set_heating_pid()

    def apply_to_cooling(self) -> None:
        kp = self.kp_spin.value()
        ki = self.ki_spin.value()
        kd = self.kd_spin.value()

        kp, ki, kd, cool_adj = self._sanitize_cooling_values(kp, ki, kd)
        if cool_adj:
            self.parent.log(
                "⚠️ Autotune-verdier klippet til sikre grenser (kjøling): " + ", ".join(cool_adj),
                "warning",
            )

        self.parent.asymmetric_controls.kp_cooling_input.setText(f"{kp:.3f}")
        self.parent.asymmetric_controls.ki_cooling_input.setText(f"{ki:.4f}")
        self.parent.asymmetric_controls.kd_cooling_input.setText(f"{kd:.3f}")
        self.parent.asymmetric_controls.set_cooling_pid()

    def apply_to_both(self) -> None:
        kp = self.kp_spin.value()
        ki = self.ki_spin.value()
        kd = self.kd_spin.value()
        kp, ki, kd, heat_adj = self._sanitize_heating_values(kp, ki, kd)
        self.kp_spin.setValue(kp)
        self.ki_spin.setValue(ki)
        self.kd_spin.setValue(kd)
        self.parent.asymmetric_controls.kp_heating_input.setText(f"{kp:.3f}")
        self.parent.asymmetric_controls.ki_heating_input.setText(f"{ki:.4f}")
        self.parent.asymmetric_controls.kd_heating_input.setText(f"{kd:.3f}")
        self.parent.asymmetric_controls.set_heating_pid()

        cool_override = self._latest_cooling_pid
        if all(value is not None for value in cool_override):
            cool_kp, cool_ki, cool_kd = cool_override  # type: ignore[misc]
            self.parent.log(
                "ℹ️ Bruker anbefalte kjøleverdier fra autotune.",
                "info",
            )
        else:
            cool_kp = kp * 0.5
            cool_ki = ki * 0.5
            cool_kd = kd * 0.5

        cool_kp, cool_ki, cool_kd, cool_adj = self._sanitize_cooling_values(cool_kp, cool_ki, cool_kd)
        if cool_adj:
            self.parent.log(
                "⚠️ Autotune-verdier klippet til sikre grenser (kjøling): " + ", ".join(cool_adj),
                "warning",
            )

        self.parent.asymmetric_controls.kp_cooling_input.setText(f"{cool_kp:.3f}")
        self.parent.asymmetric_controls.ki_cooling_input.setText(f"{cool_ki:.4f}")
        self.parent.asymmetric_controls.kd_cooling_input.setText(f"{cool_kd:.3f}")
        self.parent.asymmetric_controls.set_cooling_pid()

    def receive_data(self, data: Dict[str, Any]) -> None:
        direction = str(self.direction_combo.currentData() or "heating")
        limits = self._recommended_step_percent(self.step_spin.value(), direction)
        self._update_percent_hint(self.step_percent_spin.value(), limits)

        if self._autotune_command_sent:
            status_raw = str(data.get("autotune_status", "")).strip()
            if status_raw:
                status_readable = status_raw.replace("_", " ").title()
                self.collect_status.setText(f"Firmware-autotune: {status_readable}")
                lower = status_readable.lower()
                if lower.startswith("abort") or lower in {"aborted", "idle"}:
                    self.metric_label.setText("Autotune avbrutt av kontrolleren.")
                    self._autotune_command_sent = False
                    self.collecting = False
                    self._expected_delta = None
                    self._commanded_step_percent = None
                    self._commanded_direction = None
                    self._reported_step_clamp = False
                elif lower in {"done", "complete", "finished"}:
                    self.metric_label.setText("Firmware-autotune ferdig – analyserer data.")
                    self._autotune_command_sent = False
                    self.collecting = False
                    self._expected_delta = None
                    self._commanded_step_percent = None
                    self._commanded_direction = None
                    self._reported_step_clamp = False

        if not self.collecting:
            return
        if "cooling_plate_temp" not in data or "pid_output" not in data:
            return

        timestamp = time.time()
        temp = float(data["cooling_plate_temp"])
        output = float(data.get("pid_output", 0.0))
        self.analyzer.add_sample(timestamp, temp, output)

        if (
            self._autotune_command_sent
            and not self._reported_step_clamp
            and self._commanded_step_percent is not None
        ):
            reported_output: Optional[float] = None
            try:
                if "autotune_output" in data:
                    reported_output = float(data["autotune_output"])
                elif "pid_output" in data:
                    reported_output = float(data["pid_output"])
            except (TypeError, ValueError):
                reported_output = None

            if reported_output is not None:
                tolerance = 0.5
                commanded_direction = self._commanded_direction or "heating"
                direction_label = "varme" if commanded_direction == "heating" else "kjøle"
                if commanded_direction == "cooling":
                    reported_magnitude = abs(reported_output)
                    commanded_magnitude = abs(self._commanded_step_percent)
                else:
                    reported_magnitude = reported_output
                    commanded_magnitude = self._commanded_step_percent

                if reported_magnitude + tolerance < commanded_magnitude:
                    self.parent.log(
                        (
                            "ℹ️ Kontrolleren rapporterer "
                            f"{reported_magnitude:.1f}% {direction_label} under autotune, som er lavere enn "
                            f"forespurt {commanded_magnitude:.1f} %."
                            " Dette kan tyde på at firmware begrenser pådraget."
                        ),
                        "info",
                    )
                    self._reported_step_clamp = True

        now = time.time()
        if now - self._last_plot_update > 0.5:
            self._last_plot_update = now
            self._update_collect_plot()

        if self.analyzer.has_enough_samples():
            metrics = self.analyzer.compute_results()
            if metrics:
                normalized = self._normalize_results(metrics)
                self.metric_label.setText(
                    "ΔT: {delta} °C  |  Hastighet: {rate} °C/s  |  Overshoot: {overshoot} °C".format(
                        delta=self._format_number(normalized.get("delta_temp"), 2),
                        rate=self._format_number(normalized.get("max_rate"), 3),
                        overshoot=self._format_number(normalized.get("overshoot"), 2),
                    )
                )

                if not self._autotune_command_sent:
                    self.finish_button.setEnabled(True)
                    if self.analyzer.is_stable():
                        self.collect_status.setText("Stabilt - analyserer...")
                        self.collect_status.setStyleSheet("color: #28a745; font-weight: bold;")
                        self.collecting = False
                        self._present_results(metrics)
                else:
                    self.finish_button.setEnabled(False)
                    expected = self._expected_delta
                    delta_temp = normalized.get("delta_temp")
                    if expected is not None and delta_temp is not None:
                        if abs(delta_temp) + 0.1 < abs(expected):
                            self.collect_status.setText(
                                "Firmware-autotune kjører – responsen øker fortsatt."
                            )
                        else:
                            self.collect_status.setText(
                                "Firmware-autotune kjører – venter på resultater fra kontrolleren."
                            )
                    else:
                        self.collect_status.setText(
                            "Firmware-autotune kjører – samler flere målepunkter."
                        )
                    self.collect_status.setStyleSheet("color: #17a2b8; font-weight: bold;")
            else:
                if not self._autotune_command_sent:
                    self.finish_button.setEnabled(False)

    def _update_collect_plot(self) -> None:
        if not self._canvas:
            return

        self._axes_temp.clear()
        self._axes_output.clear()
        self._axes_temp.set_ylabel("Temp [°C]")
        self._axes_output.set_ylabel("PID [%]")
        self._axes_output.set_xlabel("Tid [s]")
        self._axes_temp.grid(True, alpha=0.3)
        self._axes_output.grid(True, alpha=0.3)

        self._axes_temp.plot(self.analyzer.timestamps, self.analyzer.temperatures, color="#ff6b35")
        self._axes_output.plot(self.analyzer.timestamps, self.analyzer.outputs, color="#1e90ff")
        self._canvas.draw()

    def _clear_plots(self) -> None:
        if self._axes_temp is not None:
            self._axes_temp.clear()
            self._axes_temp.set_ylabel("Temp [°C]")
            self._axes_temp.grid(True, alpha=0.3)
        if self._axes_output is not None:
            self._axes_output.clear()
            self._axes_output.set_ylabel("PID [%]")
            self._axes_output.set_xlabel("Tid [s]")
            self._axes_output.grid(True, alpha=0.3)
        if self._canvas is not None:
            self._canvas.draw()

    def _present_results(self, results: Dict[str, Any]) -> None:
        normalized = self._normalize_results(results)
        self._latest_results_payload = dict(normalized)
        if isinstance(normalized.get("extras"), dict):
            self._latest_results_payload["extras"] = dict(normalized["extras"])

        self.stack.setCurrentIndex(2)

        summary_lines: List[str] = []

        summary_lines.append(
            f"Varighet: {self._format_number(normalized.get('duration'), 1)} s  |  "
            f"Målepunkter: {self._format_int(normalized.get('sample_count'))}"
        )
        summary_lines.append(
            f"Baseline: {self._format_number(normalized.get('baseline_temp'), 2)} °C  |  "
            f"ΔT-mål: {self._format_number(normalized.get('target_delta'), 2)} °C"
        )

        primary_direction = normalized.get("primary_direction")
        if primary_direction:
            summary_lines.append("Retning: " + str(primary_direction).capitalize())
            summary_lines.append("")

        summary_lines.append("")
        summary_lines.append("Varme:")
        summary_lines.append(
            "  PID: Kp {kp}, Ki {ki}, Kd {kd}".format(
                kp=self._format_number(normalized.get("kp"), 3),
                ki=self._format_number(normalized.get("ki"), 3),
                kd=self._format_number(normalized.get("kd"), 3),
            )
        )
        summary_lines.append(
            "  ΔT {delta} °C  |  Maks rate {rate} °C/s  |  Gain {gain}".format(
                delta=self._format_number(normalized.get("heating_delta_temp"), 2),
                rate=self._format_number(normalized.get("heating_max_rate"), 3),
                gain=self._format_number(normalized.get("heating_process_gain"), 2),
            )
        )
        summary_lines.append(
            "  L {dead} s  |  T {tau} s  |  Overshoot {overshoot} °C  |  Steg {step} %".format(
                dead=self._format_number(normalized.get("heating_dead_time"), 2),
                tau=self._format_number(normalized.get("heating_time_constant"), 2),
                overshoot=self._format_number(normalized.get("heating_overshoot"), 2),
                step=self._format_number(normalized.get("heating_step_percent"), 1),
            )
        )
        summary_lines.append(
            "  Segment: {duration} s / {samples} punkter".format(
                duration=self._format_number(normalized.get("heating_duration"), 1),
                samples=self._format_int(normalized.get("heating_sample_count")),
            )
        )
        if not normalized.get("heating_available", True):
            reason = normalized.get("heating_reason")
            if reason:
                summary_lines.append(f"  Merknad: {reason}")

        if normalized.get("cooling_available"):
            summary_lines.append("")
            summary_lines.append("Kjøling:")
            summary_lines.append(
                "  PID: Kp {kp}, Ki {ki}, Kd {kd}".format(
                    kp=self._format_number(normalized.get("cooling_kp"), 3),
                    ki=self._format_number(normalized.get("cooling_ki"), 3),
                    kd=self._format_number(normalized.get("cooling_kd"), 3),
                )
            )
            summary_lines.append(
                "  ΔT {delta} °C  |  Maks rate {rate} °C/s  |  Gain {gain}".format(
                    delta=self._format_number(normalized.get("cooling_delta_temp"), 2),
                    rate=self._format_number(normalized.get("cooling_max_rate"), 3),
                    gain=self._format_number(normalized.get("cooling_process_gain"), 2),
                )
            )
            summary_lines.append(
                "  L {dead} s  |  T {tau} s  |  Overshoot {overshoot} °C  |  Steg {step} %".format(
                    dead=self._format_number(normalized.get("cooling_dead_time"), 2),
                    tau=self._format_number(normalized.get("cooling_time_constant"), 2),
                    overshoot=self._format_number(normalized.get("cooling_overshoot"), 2),
                    step=self._format_number(normalized.get("cooling_step_percent"), 1),
                )
            )
            summary_lines.append(
                "  Segment: {duration} s / {samples} punkter".format(
                    duration=self._format_number(normalized.get("cooling_duration"), 1),
                    samples=self._format_int(normalized.get("cooling_sample_count")),
                )
            )
        else:
            reason = normalized.get("cooling_reason")
            if reason:
                summary_lines.append("")
                summary_lines.append(f"Kjøling: {reason}")

        extras = normalized.get("extras") or {}
        if isinstance(extras, dict) and extras:
            summary_lines.append("")
            for key, value in extras.items():
                if key in {"raw_data", "samples"}:
                    continue
                summary_lines.append(f"{key}: {value}")

        summary_text = "\n".join(summary_lines)
        self.results_summary.setText(summary_text)

        kp_source = normalized.get("kp")
        ki_source = normalized.get("ki")
        kd_source = normalized.get("kd")
        missing_pid = [
            label
            for label, value in (("Kp", kp_source), ("Ki", ki_source), ("Kd", kd_source))
            if value is None
        ]

        kp_input = kp_source if kp_source is not None else self.kp_spin.value()
        ki_input = ki_source if ki_source is not None else self.ki_spin.value()
        kd_input = kd_source if kd_source is not None else self.kd_spin.value()

        kp, ki, kd, adjustments = self._sanitize_heating_values(kp_input, ki_input, kd_input)
        self.kp_spin.setValue(kp)
        self.ki_spin.setValue(ki)
        self.kd_spin.setValue(kd)
        self._update_limit_notice(adjustments)

        if adjustments:
            self.parent.log(
                "⚠️ Autotune-verdier klippet til sikre grenser (varme): " + ", ".join(adjustments),
                "warning",
            )

        if missing_pid:
            warning_text = "⚠️ Resultatet mangler PID-komponenter: " + ", ".join(missing_pid)
            self.parent.log(warning_text, "warning")
            if hasattr(self, "limit_notice"):
                self.limit_notice.setText(warning_text)
                self.limit_notice.show()

        if self._result_axes is not None and self._result_canvas is not None:
            self._result_axes.clear()
            self._result_axes.set_title("Temperaturrespons")
            self._result_axes.set_xlabel("Tid [s]")
            self._result_axes.set_ylabel("Temp [°C]")
            self._result_axes.grid(True, alpha=0.3)
            if self.analyzer.timestamps and self.analyzer.temperatures:
                self._result_axes.plot(
                    self.analyzer.timestamps,
                    self.analyzer.temperatures,
                    color="#ff6b35",
                    label="Plate temp",
                )
                self._result_axes.legend()
            self._result_canvas.draw()

        if all(
            value is not None
            for value in (
                normalized.get("cooling_kp"),
                normalized.get("cooling_ki"),
                normalized.get("cooling_kd"),
            )
        ):
            self._latest_cooling_pid = (
                float(normalized["cooling_kp"]),
                float(normalized["cooling_ki"]),
                float(normalized["cooling_kd"]),
            )
        else:
            self._latest_cooling_pid = (None, None, None)

        self._autotune_command_sent = False
        self._expected_delta = None
        self._restore_original_target()

    def display_results(self, results: Dict[str, Any]) -> None:
        """Expose results rendering to the parent GUI."""
        self.collecting = False
        self._present_results(results)

    def _update_limit_notice(self, adjustments: List[str]) -> None:
        if not hasattr(self, "limit_notice"):
            return
        if adjustments:
            self.limit_notice.setText(
                "⚠️ Verdiene ble justert til sikre grenser: " + ", ".join(adjustments)
            )
            self.limit_notice.show()
        else:
            self.limit_notice.hide()

    def _recommended_step_percent(self, step_delta: float, direction: str) -> Dict[str, float]:
        latest_data = getattr(self.parent, "last_status_data", {}) or {}
        direction = direction or "heating"
        step_delta = abs(step_delta)

        if direction == "cooling":
            limit_key = "pid_cooling_limit"
            fallback_attr = "last_cooling_limit"
            limit_label = "kjøle"
        else:
            limit_key = "pid_heating_limit"
            fallback_attr = "last_heating_limit"
            limit_label = "varme"

        try:
            primary_limit = float(latest_data.get(limit_key, 0.0))
        except (TypeError, ValueError):
            primary_limit = 0.0

        if primary_limit <= 0.0:
            try:
                primary_limit = float(getattr(self.parent, fallback_attr, 0.0))
            except (TypeError, ValueError):
                primary_limit = 0.0

        try:
            pid_limit = float(latest_data.get("pid_max_output", primary_limit))
        except (TypeError, ValueError):
            pid_limit = primary_limit

        primary_limit = max(0.0, primary_limit)
        pid_limit = max(0.0, pid_limit)

        device_candidates: List[float] = []
        for value in (primary_limit, pid_limit):
            if value > 0.0:
                device_candidates.append(value)
        device_cap = min(device_candidates) if device_candidates else 0.0
        if device_cap > 0.0:
            device_cap = min(device_cap, 100.0)

        safety_cap = 0.0
        if primary_limit > 0.0:
            safety_cap = min(primary_limit * self.MANUAL_STEP_SAFETY_FRACTION, primary_limit)

        percent = max(0.0, step_delta * self.PERCENT_PER_DEGREE)
        auto_cap = safety_cap or device_cap or 0.0
        if auto_cap > 0.0:
            if percent < self.MIN_STEP_PERCENT <= auto_cap:
                percent = self.MIN_STEP_PERCENT
            percent = min(percent, auto_cap)

        return {
            "recommended": float(percent),
            "device_cap": float(device_cap),
            "pid_limit": float(pid_limit),
            "safety_cap": float(safety_cap),
            "primary_limit": float(primary_limit),
            "limit_label": limit_label,
            "direction": direction,
        }

    def _handle_step_changed(self, value: float) -> None:
        direction = self.direction_combo.currentData() or "heating"
        limits = self._recommended_step_percent(value, str(direction))
        recommended = limits["recommended"]
        if not self._percent_user_override:
            self._updating_percent_spin = True
            with QSignalBlocker(self.step_percent_spin):
                self.step_percent_spin.setValue(recommended)
            self._updating_percent_spin = False
        self._update_percent_hint(self.step_percent_spin.value(), limits)

    def _handle_percent_changed(self, value: float) -> None:
        if self._updating_percent_spin:
            return
        self._percent_user_override = True
        direction = self.direction_combo.currentData() or "heating"
        limits = self._recommended_step_percent(self.step_spin.value(), str(direction))
        self._update_percent_hint(value, limits)

    def _handle_direction_changed(self, index: int) -> None:
        direction = self.direction_combo.itemData(index) or "heating"
        limits = self._recommended_step_percent(self.step_spin.value(), str(direction))
        self._percent_user_override = False
        self._updating_percent_spin = True
        with QSignalBlocker(self.step_percent_spin):
            self.step_percent_spin.setValue(limits["recommended"])
        self._updating_percent_spin = False
        self._update_percent_hint(self.step_percent_spin.value(), limits)

    def _update_percent_hint(
        self, selected: float, limits: Dict[str, float]
    ) -> None:
        if not hasattr(self, "percent_hint_label"):
            return

        direction = str(limits.get("direction", "heating"))
        limit_label = str(limits.get("limit_label", "varme"))
        primary_limit = limits.get("primary_limit", 0.0) or 0.0
        device_cap = limits.get("device_cap", primary_limit) or 0.0
        pid_limit = limits.get("pid_limit", primary_limit) or 0.0
        safety_cap = limits.get("safety_cap", primary_limit * self.MANUAL_STEP_SAFETY_FRACTION) or 0.0
        recommended = limits.get("recommended", selected)

        limit_note: str
        tolerance = 0.1
        cap_phrase = "varme-pådrag" if direction == "heating" else "kjøle-pådrag"
        if device_cap and abs(primary_limit - device_cap) <= tolerance:
            limit_note = f"Maksimalt {cap_phrase} er {primary_limit:.1f} %."
        else:
            reasons = []
            if device_cap and pid_limit and device_cap <= pid_limit + tolerance and pid_limit < primary_limit - tolerance:
                reasons.append(f"PID-grensen ({pid_limit:.1f} %)")
            safety_value = safety_cap
            safety_percent = self.MANUAL_STEP_SAFETY_FRACTION * 100.0
            if (
                safety_value
                and device_cap
                and device_cap <= safety_value + tolerance
                and safety_value < primary_limit - tolerance
            ):
                reasons.append(f"{safety_percent:.0f}% av {limit_label}-grensen ({safety_value:.1f} %)")
            if not reasons:
                if device_cap:
                    reasons.append(f"øvre grense {device_cap:.1f} %")
                else:
                    reasons.append("ingen rapportert grense")
            reason_text = ", ".join(reasons)
            limit_note = (
                f"Maksimalt {cap_phrase} er {primary_limit:.1f} %, men wizzarden foreslår {recommended:.1f} % "
                f"({reason_text})."
            )

        self.percent_hint_label.setText(
            (
                f"Anbefalt manuelt pådrag (≈{self.PERCENT_PER_DEGREE:.0f} % pr °C): {recommended:.1f} %. "
                f"Valgt manuelt pådrag: {selected:.1f} %. "
                f"{limit_note} Du kan overstyre verdien ved å endre feltet over."
            )
        )

    def _restore_original_target(self) -> None:
        if self._original_target is None:
            return

        current_target = self.parent.current_target_temp
        if current_target is not None and abs(current_target - self._original_target) < 0.05:
            self._original_target = None
            return

        if self.parent.send_target_temperature(
            self._original_target,
            source="autotune gjenopprett",
            silent=True,
        ):
            self.parent.log(
                f"🎯 Autotune: måltemperatur tilbake til {self._original_target:.2f} °C",
                "info",
            )
        self._original_target = None



# ============================================================================
# 2. KEEP ALL THE EXISTING CLASSES (MatplotlibGraphWidget, etc.) UNCHANGED
# ============================================================================

class MatplotlibGraphWidget(QWidget):
    """Stable matplotlib widget with proven functionality"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.auto_scale_enabled = True
        self.setup_plots()
        self.setup_layout()
        self.max_points = 200
        self.update_counter = 0
        self._last_time_data: List[float] = []
        self._last_graph_data: Dict[str, List] = {}
        print("✅ MatplotlibGraphWidget initialized")

    def setup_plots(self):
        """Create matplotlib figure with optimized settings"""
        try:
            self.figure = Figure(figsize=(12, 8), facecolor='white', constrained_layout=True)
            self.canvas = FigureCanvas(self.figure)

            # Create subplots
            gs = self.figure.add_gridspec(3, 1, height_ratios=[2, 1, 1], hspace=0.3)
            
            # Temperature subplot
            self.ax_temp = self.figure.add_subplot(gs[0])
            self.ax_temp.set_title('Temperature Monitoring', fontsize=14, fontweight='bold')
            self.ax_temp.set_ylabel('Temperature (°C)', fontsize=12)
            self.ax_temp.grid(True, alpha=0.3)
            self.ax_temp.set_facecolor('#f8f9fa')
            
            # PID subplot (share X axis for synchronized zoom/pan)
            self.ax_pid = self.figure.add_subplot(gs[1], sharex=self.ax_temp)
            self.ax_pid.set_title('PID Output', fontsize=12, fontweight='bold')
            self.ax_pid.set_ylabel('PID Output', fontsize=11)
            self.ax_pid.grid(True, alpha=0.3)
            self.ax_pid.set_facecolor('#f0f8ff')
            
            # Breath subplot (share X axis for synchronized zoom/pan)
            self.ax_breath = self.figure.add_subplot(gs[2], sharex=self.ax_temp)
            self.ax_breath.set_title('Breath Frequency', fontsize=12, fontweight='bold')
            self.ax_breath.set_xlabel('Time (seconds)', fontsize=12)
            self.ax_breath.set_ylabel('BPM', fontsize=11)
            self.ax_breath.grid(True, alpha=0.3)
            self.ax_breath.set_facecolor('#fff8f0')
            
            # Initialize lines
            self.line_plate, = self.ax_temp.plot([], [], 'r-o', linewidth=3, markersize=4,
                                               label='Cooling Plate', alpha=0.8)
            self.line_rectal, = self.ax_temp.plot([], [], 'g-s', linewidth=3, markersize=4,
                                                label='Rectal Probe', alpha=0.8)
            self.line_target, = self.ax_temp.plot([], [], 'b--', linewidth=2,
                                                label='Target', alpha=0.7)
            self.line_rectal_setpoint, = self.ax_temp.plot([], [], 'k-.', linewidth=2,
                                                          label='Rectal Setpoint', alpha=0.7)
            self.line_adjusted_target, = self.ax_temp.plot([], [], color='#ff6f00', linewidth=2,
                                                          linestyle=':', label='Rectal-adjusted Target', alpha=0.9)

            self.line_pid, = self.ax_pid.plot([], [], 'purple', linewidth=2.5,
                                            label='PID Output', alpha=0.8)
            
            self.line_breath, = self.ax_breath.plot([], [], 'orange', linewidth=2.5, 
                                                  label='Breath Rate', alpha=0.8)
            
            # Add legends
            self.ax_temp.legend(loc='upper right', fontsize=10)
            self.ax_pid.legend(loc='upper right', fontsize=9)
            self.ax_breath.legend(loc='upper right', fontsize=9)
            
            # Set initial ranges
            self.set_initial_ranges()

            # Enable smooth zooming with mouse wheel
            self.canvas.mpl_connect('scroll_event', self._handle_scroll_zoom)
            self.canvas.mpl_connect('button_press_event', self._handle_mouse_action)
            self.canvas.mpl_connect('button_release_event', self._handle_mouse_action)

            print("✅ Matplotlib plots configured")
            
        except Exception as e:
            print(f"❌ Plot setup error: {e}")
            raise

    def setup_layout(self):
        """Setup widget layout"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        toolbar = NavigationToolbar2QT(self.canvas, self)
        layout.addWidget(toolbar)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        self.auto_follow_checkbox = QCheckBox("🔄 Auto-follow")
        self.auto_follow_checkbox.setChecked(True)
        self.auto_follow_checkbox.toggled.connect(self._toggle_auto_follow)
        controls.addWidget(self.auto_follow_checkbox)

        reset_btn = QPushButton("Reset view")
        reset_btn.clicked.connect(self.reset_zoom)
        controls.addWidget(reset_btn)
        controls.addStretch(1)

        layout.addLayout(controls)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def set_initial_ranges(self):
        """Set initial ranges"""
        self.ax_temp.set_xlim(0, 60)
        self.ax_temp.set_ylim(10, 45)
        self.ax_pid.set_xlim(0, 60)
        self.ax_pid.set_ylim(-100, 100)
        self.ax_breath.set_xlim(0, 60)
        self.ax_breath.set_ylim(0, 160)

    def update_graphs(self, graph_data: Dict[str, List]) -> bool:
        """Update all graphs with new data"""
        try:
            self.update_counter += 1

            if not graph_data.get("time") or len(graph_data["time"]) == 0:
                return False

            time_data = graph_data["time"]
            self._last_time_data = time_data
            self._last_graph_data = graph_data
            
            # Update lines
            if "plate_temp" in graph_data:
                self.line_plate.set_data(time_data, graph_data["plate_temp"])
            if "rectal_temp" in graph_data:
                self.line_rectal.set_data(time_data, graph_data["rectal_temp"])
            if "target_temp" in graph_data:
                self.line_target.set_data(time_data, graph_data["target_temp"])
            if "rectal_target_temp" in graph_data:
                rectal_targets = graph_data["rectal_target_temp"]
                if rectal_targets:
                    self.line_rectal_setpoint.set_data(time_data, rectal_targets)
                    has_valid = any(math.isfinite(value) for value in rectal_targets)
                    self.line_rectal_setpoint.set_visible(has_valid)
                else:
                    self.line_rectal_setpoint.set_data([], [])
                    self.line_rectal_setpoint.set_visible(False)
            if "adjusted_target_temp" in graph_data:
                adjusted = graph_data["adjusted_target_temp"]
                if adjusted:
                    self.line_adjusted_target.set_data(time_data, adjusted)
                    has_valid = any(math.isfinite(value) for value in adjusted)
                    self.line_adjusted_target.set_visible(has_valid)
                else:
                    self.line_adjusted_target.set_data([], [])
                    self.line_adjusted_target.set_visible(False)
            if "pid_output" in graph_data:
                self.line_pid.set_data(time_data, graph_data["pid_output"])
            if "breath_rate" in graph_data:
                self.line_breath.set_data(time_data, graph_data["breath_rate"])

            # Auto-scale
            self.auto_scale_axes(time_data, graph_data)
            
            # Redraw
            self.canvas.draw_idle()
            
            if self.update_counter % 10 == 1:
                print(f"📊 Graph update #{self.update_counter}: {len(time_data)} points")
            
            return True
            
        except Exception as e:
            print(f"❌ Graph update error: {e}")
            return False

    def auto_scale_axes(self, time_data: List[float], graph_data: Dict[str, List]):
        """Auto-scale axes"""
        try:
            if hasattr(self, "auto_follow_checkbox"):
                self.auto_scale_enabled = self.auto_follow_checkbox.isChecked()
            if not self.auto_scale_enabled:
                return
            if len(time_data) < 2:
                return
            
            # X-axis
            time_min, time_max = min(time_data), max(time_data)
            if time_max - time_min > 60:
                x_min = time_max - 60
                x_max = time_max + 5
            else:
                x_min = time_min - 2
                x_max = time_max + 5
            
            for ax in [self.ax_temp, self.ax_pid, self.ax_breath]:
                ax.set_xlim(x_min, x_max)
            
            # Y-axis auto-scaling
            if graph_data.get("plate_temp") and graph_data.get("rectal_temp"):
                combined_temps = graph_data["plate_temp"] + graph_data["rectal_temp"] + graph_data["target_temp"]
                if graph_data.get("adjusted_target_temp"):
                    combined_temps += [val for val in graph_data["adjusted_target_temp"] if math.isfinite(val)]
                if graph_data.get("rectal_target_temp"):
                    combined_temps += [val for val in graph_data["rectal_target_temp"] if math.isfinite(val)]
                all_temps = combined_temps
                temp_min, temp_max = min(all_temps), max(all_temps)
                margin = max((temp_max - temp_min) * 0.1, 2.0)
                self.ax_temp.set_ylim(temp_min - margin, temp_max + margin)
            
            if graph_data.get("pid_output"):
                pid_values = graph_data["pid_output"]
                pid_min, pid_max = min(pid_values), max(pid_values)
                margin = max((pid_max - pid_min) * 0.1, 10.0)
                self.ax_pid.set_ylim(pid_min - margin, pid_max + margin)
            
            if graph_data.get("breath_rate"):
                breath_values = [max(0, b) for b in graph_data["breath_rate"]]
                if breath_values:
                    breath_min, breath_max = min(breath_values), max(breath_values)
                    margin = max((breath_max - breath_min) * 0.1, 10.0)
                    self.ax_breath.set_ylim(max(0, breath_min - margin), breath_max + margin)
            
        except Exception as e:
            print(f"⚠️ Auto-scale error: {e}")

    def clear_graphs(self):
        """Clear all graphs"""
        try:
            self.line_plate.set_data([], [])
            self.line_rectal.set_data([], [])
            self.line_target.set_data([], [])
            self.line_rectal_setpoint.set_data([], [])
            self.line_adjusted_target.set_data([], [])
            self.line_pid.set_data([], [])
            self.line_breath.set_data([], [])

            self.set_initial_ranges()
            self.canvas.draw()
            
            self.update_counter = 0
            print("🧹 Graphs cleared")
            
        except Exception as e:
            print(f"❌ Clear graphs error: {e}")

    def generate_test_data(self) -> Dict[str, List]:
        """Generate test data"""
        try:
            import math
            
            times = list(range(50))
            plate_temps = [37 - 15 * (1 - math.exp(-t/20)) + math.sin(t/5) * 0.8 for t in times]
            rectal_temps = [37 - 8 * (1 - math.exp(-t/30)) + math.sin(t/8) * 0.5 for t in times]
            target_temps = [25 + 5 * math.sin(t/15) for t in times]
            rectal_targets = [
                32.0 if t < 20 else 30.0 if t < 35 else 36.0 for t in times
            ]
            pid_outputs = [50 * math.sin(t/10) + 20 * math.sin(t/3) for t in times]
            breath_rates = [max(5, 150 * math.exp(-t/40) + 10 + math.sin(t/4) * 8) for t in times]
            adjusted_targets = [target_temps[i] + (1.5 if i > 20 else 0.0) for i in range(len(times))]

            return {
                "time": times,
                "plate_temp": plate_temps,
                "rectal_temp": rectal_temps,
                "target_temp": target_temps,
                "rectal_target_temp": rectal_targets,
                "adjusted_target_temp": adjusted_targets,
                "pid_output": pid_outputs,
                "breath_rate": breath_rates
            }

        except Exception as e:
            print(f"❌ Test data error: {e}")
            return {
                "time": [],
                "plate_temp": [],
                "rectal_temp": [],
                "target_temp": [],
                "rectal_target_temp": [],
                "adjusted_target_temp": [],
                "pid_output": [],
                "breath_rate": [],
            }

    def _handle_mouse_action(self, event):
        """Disable auto-scaling when the user pans/zooms."""
        if event.inaxes:
            if hasattr(self, "auto_follow_checkbox"):
                with QSignalBlocker(self.auto_follow_checkbox):
                    self.auto_follow_checkbox.setChecked(False)
            self.auto_scale_enabled = False

    def _handle_scroll_zoom(self, event):
        """Smooth zoom for both axes centered around the cursor."""
        if event.inaxes is None:
            return

        self.auto_scale_enabled = False

        if hasattr(self, "auto_follow_checkbox"):
            with QSignalBlocker(self.auto_follow_checkbox):
                self.auto_follow_checkbox.setChecked(False)

        scale_factor = 0.9 if event.button == 'up' else 1.1

        # Compute new X range from the axis under the cursor and apply to all axes.
        x_min, x_max = event.inaxes.get_xlim()
        x_center = event.xdata if event.xdata is not None else (x_min + x_max) / 2
        new_x_range = (x_max - x_min) * scale_factor
        new_xlim = (x_center - new_x_range / 2, x_center + new_x_range / 2)

        for ax in (self.ax_temp, self.ax_pid, self.ax_breath):
            ax.set_xlim(new_xlim)

        # Only scale Y on the axis being interacted with.
        y_min, y_max = event.inaxes.get_ylim()
        y_center = event.ydata if event.ydata is not None else (y_min + y_max) / 2
        new_y_range = (y_max - y_min) * scale_factor
        event.inaxes.set_ylim(y_center - new_y_range / 2, y_center + new_y_range / 2)

        self.canvas.draw_idle()

    def reset_zoom(self):
        """Return to automatic scaling."""
        self.auto_scale_enabled = True
        if hasattr(self, "auto_follow_checkbox"):
            with QSignalBlocker(self.auto_follow_checkbox):
                self.auto_follow_checkbox.setChecked(True)
        self.set_initial_ranges()
        self.canvas.draw_idle()

    def _toggle_auto_follow(self, checked: bool):
        """Turn auto-follow on/off, restoring view when re-enabled."""

        self.auto_scale_enabled = checked
        if checked and self._last_time_data and self._last_graph_data:
            self.auto_scale_axes(self._last_time_data, self._last_graph_data)
        self.canvas.draw_idle()


class CalibrationTab(QWidget):
    """Calibration is disabled in the recovery configuration."""

    def __init__(self, main_window: "MainWindow"):
        super().__init__(main_window)
        self.main_window = main_window
        self.calibration_entries: List[Dict[str, Any]] = []
        self._last_plate_raw: Optional[float] = None
        self._last_plate_cal: Optional[float] = None
        self._last_rectal_raw: Optional[float] = None
        self._last_rectal_cal: Optional[float] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        notice = QLabel(
            "Kalibrering er deaktivert i denne stabile versjonen. "
            "Sensorene bruker råmålinger med enkle offset-verdier, og GUI-en "
            "sender derfor ingen kalibreringskommandoer."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)

        self.setLayout(layout)

    def update_raw_values(
        self,
        plate_raw: Optional[float],
        plate_cal: Optional[float],
        rectal_raw: Optional[float],
        rectal_cal: Optional[float],
    ):
        # Preserve latest readings for potential future display/logging
        if plate_raw is not None:
            self._last_plate_raw = plate_raw
        if plate_cal is not None:
            self._last_plate_cal = plate_cal
        if rectal_raw is not None:
            self._last_rectal_raw = rectal_raw
        if rectal_cal is not None:
            self._last_rectal_cal = rectal_cal

    def _add_calibration_point(self):
        self.main_window.log(
            "⚠️ Kalibrering er deaktivert i denne builden; ignorere forespørsel om å legge til punkt.",
            "warning",
        )

    def _commit_calibration(self):
        self.main_window.log(
            "⚠️ Kalibrering er deaktivert; ingen data å lagre.",
            "warning",
        )

    def _export_calibration(self):
        self.main_window.log(
            "⚠️ Kalibrering er deaktivert; ingen data å eksportere.",
            "warning",
        )

    def request_table(self, sensor: Optional[str] = None):
        self.main_window.log(
            "ℹ️ Kalibreringstabeller støttes ikke i denne stabile versjonen.",
            "info",
        )

    def update_table(self, payload: Dict[str, Any]):
        self.calibration_entries = []
        self.main_window.log(
            "ℹ️ Ignorerer mottatt kalibreringsdata fordi funksjonen er deaktivert.",
            "info",
        )

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        print("🚀 Initializing GUI v3.0...")
        
        self.setWindowTitle("🧪 Musehypothermi GUI v3.0 - Asymmetric PID Edition")
        self.setMinimumSize(1200, 800)
        
        # Adjust to screen
        screen = QApplication.primaryScreen().availableGeometry()
        width = min(1600, screen.width() - 100)
        height = min(1000, screen.height() - 100)
        self.resize(width, height)
        
        # Initialize data
        self.init_data_structures()
        
        # Create UI
        self.init_ui()
        
        # Initialize managers
        self.init_managers()
        
        print("✅ GUI v3.0 initialized!")

    def init_data_structures(self):
        """Initialize data structures"""
        self.graph_data = {
            "time": [],
            "plate_temp": [],
            "rectal_temp": [],
            "pid_output": [],
            "breath_rate": [],
            "target_temp": [],
            "rectal_target_temp": [],
            "adjusted_target_temp": [],
        }

        self.connection_established = False
        self.data_logger: Optional[Logger] = None
        self.start_time = None
        self.max_graph_points = 200
        self.data_update_count = 0
        self.graph_update_count = 0
        self.last_heating_limit = 35.0
        self.last_cooling_limit = 35.0
        self.last_equilibrium_temp: Optional[float] = None
        self.last_equilibrium_valid: bool = False
        self.equilibrium_estimating: bool = False
        self.equilibrium_comp_enabled: bool = False
        self.failsafe_active: bool = False
        self.last_failsafe_reason: str = ""
        self.panic_active: bool = False
        self.pc_failsafe_dialog_shown = False
        self.emergency_event_history: List[str] = []
        self.emergency_stop_active: bool = False
        self.profile_data = []
        self.profile_steps = []
        self.profile_ready = False
        self.profile_upload_pending = False
        self.profile_active = False
        self.profile_paused = False
        self.rectal_setpoint_schedule: List[Tuple[float, float, float]] = []
        self.profile_run_start_time: Optional[float] = None
        self.profile_pause_time: Optional[float] = None
        self.profile_elapsed_paused: float = 0.0
        self.current_plate_temp: Optional[float] = None
        self.current_target_temp: Optional[float] = None
        self.pid_mode: Optional[str] = None
        self.pid_running: bool = False
        self.last_status_data: Dict[str, Any] = {}
        self.serial_monitor_tx_lines: List[str] = []
        self.serial_monitor_rx_lines: List[str] = []
        self.serial_monitor_max_lines = 500
        self.disable_breath_check: bool = False
        self.breath_suppression_notified: bool = False

        print("✅ Data structures initialized")

    def init_ui(self):
        """Initialize UI"""
        try:
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            main_layout = QVBoxLayout()
            central_widget.setLayout(main_layout)
            
            # Tab widget
            self.tab_widget = QTabWidget()
            main_layout.addWidget(self.tab_widget)
            
            # Create tabs
            self.create_control_tab()
            self.create_monitoring_tab()
            self.create_autotune_tab()
            self.create_profile_tab()
            self.create_serial_monitor_tab()
            self.create_calibration_tab()
            
            # ============================================================================
            print("✅ UI initialized")
            
        except Exception as e:
            print(f"❌ UI error: {e}")
            raise

    # ============================================================================
    # 5. ADD THIS NEW METHOD FOR ASYMMETRIC COMMANDS
    # ============================================================================
    
    def send_asymmetric_command(self, command: str, params: Dict) -> bool:
        """Send asymmetric PID command with connection check"""
        if not self.connection_established:
            self.log("❌ Not connected", "error")
            return False
        
        try:
            cmd = {"CMD": {"action": command, "params": params}}
            self.serial_manager.send(json.dumps(cmd))
            self.event_logger.log_event(f"ASYMMETRIC_CMD: {command} → {params}")
            return True
        except Exception as e:
            self.log(f"❌ Asymmetric command error: {e}", "error")
            return False

    def create_control_tab(self):
        """Create control tab"""
        control_widget = QWidget()
        control_layout = QHBoxLayout()
        control_widget.setLayout(control_layout)
        
        # Left panel
        left_panel = self.create_control_panel()
        left_panel.setMaximumWidth(520)
        
        # Right panel
        right_panel = self.create_live_data_panel()
        right_panel.setMaximumWidth(480)
        
        control_layout.addWidget(left_panel)
        control_layout.addWidget(right_panel)
        control_layout.addStretch()
        
        self.tab_widget.addTab(control_widget, "🎛️ Control")

    def create_control_panel(self):
        """Create control panel with connection"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # CONNECTION SECTION
        conn_group = QGroupBox("🔌 Serial Connection")
        conn_layout = QVBoxLayout()
        
        # Port row
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Port:"))
        
        self.portSelector = QComboBox()
        self.portSelector.setMinimumWidth(140)
        port_row.addWidget(self.portSelector)
        
        self.refreshButton = QPushButton("🔄")
        self.refreshButton.setFixedSize(36, 28)
        self.refreshButton.clicked.connect(self.refresh_ports)
        port_row.addWidget(self.refreshButton)
        
        self.connectButton = QPushButton("Connect")
        self.connectButton.setFixedWidth(100)
        self.connectButton.clicked.connect(self.toggle_connection)
        port_row.addWidget(self.connectButton)
        
        port_row.addStretch()
        
        # Status row
        status_row = QHBoxLayout()
        
        self.connectionStatusLabel = QLabel("❌ Disconnected")
        self.connectionStatusLabel.setStyleSheet("color: red; font-weight: bold;")
        status_row.addWidget(self.connectionStatusLabel)

        self.failsafeIndicator = QLabel("🟢 Safe")
        self.failsafeIndicator.setStyleSheet("color: green; font-weight: bold;")
        self.failsafeLabel = self.failsafeIndicator
        status_row.addWidget(self.failsafeIndicator)
        
        self.pidStatusIndicator = QLabel("⚫ PID Off")
        self.pidStatusIndicator.setStyleSheet("color: gray; font-weight: bold;")
        status_row.addWidget(self.pidStatusIndicator)

        self.equilibriumLabel = QLabel("Equilibrium: --")
        self.equilibriumLabel.setStyleSheet("color: #555; font-weight: bold;")
        status_row.addWidget(self.equilibriumLabel)

        status_row.addStretch()

        # Equilibrium controls
        equilibrium_row = QHBoxLayout()
        self.equilibriumEstimateButton = QPushButton("Estimate Equilibrium")
        self.equilibriumEstimateButton.setCursor(Qt.PointingHandCursor)
        self.equilibriumEstimateButton.clicked.connect(self.request_equilibrium_estimate)
        equilibrium_row.addWidget(self.equilibriumEstimateButton)

        self.equilibriumStateLabel = QLabel("Equilibrium: idle")
        self.equilibriumStateLabel.setStyleSheet("color: #6c757d; font-weight: bold;")
        equilibrium_row.addWidget(self.equilibriumStateLabel)

        self.equilibriumCompCheckbox = QCheckBox("Use equilibrium compensation")
        self.equilibriumCompCheckbox.stateChanged.connect(self.toggle_equilibrium_compensation)
        equilibrium_row.addWidget(self.equilibriumCompCheckbox)

        equilibrium_row.addStretch()
        
        # Emergency row
        emergency_row = QHBoxLayout()
        
        self.panicButton = QPushButton("🚨 PANIC")
        self.panicButton.setFixedSize(110, 38)
        self.panicButton.setStyleSheet("""
            QPushButton {
                background-color: #dc3545; 
                color: white; 
                font-weight: bold; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.panicButton.clicked.connect(self.trigger_panic)
        emergency_row.addWidget(self.panicButton)
        emergency_row.addStretch()

        conn_layout.addLayout(port_row)
        conn_layout.addLayout(status_row)
        conn_layout.addLayout(equilibrium_row)
        conn_layout.addLayout(emergency_row)
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # ASYMMETRIC PID CONTROLS
        self.asymmetric_controls = AsymmetricPIDControls(self)
        layout.addWidget(self.asymmetric_controls)
        
        # PID CONTROL
        control_group = QGroupBox("🚀 PID Control")
        control_layout = QHBoxLayout()

        self.startPIDButton = QPushButton("▶️ START")
        self.startPIDButton.clicked.connect(lambda: self.send_and_log_cmd("pid", "start"))
        self.startPIDButton.setCursor(Qt.PointingHandCursor)
        self.startPIDButton.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #34c759;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)

        self.stopPIDButton = QPushButton("⏹️ STOP")
        self.stopPIDButton.clicked.connect(lambda: self.send_and_log_cmd("pid", "stop"))
        self.stopPIDButton.setCursor(Qt.PointingHandCursor)
        self.stopPIDButton.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ff5c6c;
            }
            QPushButton:pressed {
                background-color: #b02a37;
            }
        """)

        control_layout.addWidget(self.startPIDButton)
        control_layout.addWidget(self.stopPIDButton)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # TARGET TEMPERATURE CONTROLS
        target_group = QGroupBox("🎯 Target Temperature")
        target_layout = QHBoxLayout()
        target_layout.setSpacing(12)

        self.setpointInput = QLineEdit("37.0")
        self.setpointInput.setMinimumWidth(120)
        self.setpointInput.setAlignment(Qt.AlignCenter)

        self.setSetpointButton = QPushButton("Set Target")
        self.setSetpointButton.clicked.connect(self.set_manual_setpoint)
        self.setSetpointButton.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")

        target_layout.addWidget(QLabel("Target:"))
        target_layout.addWidget(self.setpointInput)
        target_layout.addWidget(QLabel("°C"))
        target_layout.addWidget(self.setSetpointButton)
        target_layout.addStretch()

        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        layout.addStretch()
        return panel

    def toggle_breath_check(self, state: int):
        """Enable/disable suppression of breath-stop failsafes."""
        self.disable_breath_check = bool(state)
        self.breath_suppression_notified = False

        if self.disable_breath_check:
            self.log("⚠️ Breath-stop check disabled (test mode)", "warning")
            self.event_logger.log_event("EVENT: breath_check_disabled")
            if self.serial_manager.is_connected():
                self.serial_manager.sendSET("breath_check_enabled", False)
        else:
            self.log("✅ Breath-stop check enabled", "info")
            self.event_logger.log_event("EVENT: breath_check_enabled")
            if self.serial_manager.is_connected():
                self.serial_manager.sendSET("breath_check_enabled", True)

    def create_live_data_panel(self):
        """Create live data display"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # System status group (shown above live data)
        status_group = QGroupBox("📡 System Status")
        status_layout = QGridLayout()

        self.regulationModeValue = QLabel("Unknown")
        self.regulationModeValue.setStyleSheet("font-weight: bold; color: #6c757d;")
        self.temperatureRateValue = QLabel("0.000 °C/s")
        self.temperatureRateValue.setStyleSheet("font-weight: bold; color: #28a745;")
        self.emergencyStateValue = QLabel("✅ Clear")
        self.emergencyStateValue.setStyleSheet("font-weight: bold; color: #28a745;")

        status_layout.addWidget(QLabel("Regulation Mode:"), 0, 0)
        status_layout.addWidget(self.regulationModeValue, 0, 1)
        status_layout.addWidget(QLabel("Temp Rate:"), 1, 0)
        status_layout.addWidget(self.temperatureRateValue, 1, 1)
        status_layout.addWidget(QLabel("Emergency:"), 2, 0)
        status_layout.addWidget(self.emergencyStateValue, 2, 1)
        status_layout.setColumnStretch(1, 1)
        status_layout.setHorizontalSpacing(12)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        if hasattr(self, "asymmetric_controls"):
            self.asymmetric_controls.register_status_labels(
                self.regulationModeValue,
                self.temperatureRateValue,
                self.emergencyStateValue,
            )
            if hasattr(self.asymmetric_controls, "status_group"):
                self.asymmetric_controls.status_group.setVisible(False)

        # Live data group
        data_group = QGroupBox("📊 Live Data")
        data_layout = QGridLayout()
        
        # Temperature displays
        self.plateTempDisplay = QLabel("22.0°C")
        self.plateTempDisplay.setStyleSheet("""
            font-family: 'Courier New'; 
            font-size: 16px; 
            font-weight: bold; 
            color: #dc3545;
            background-color: #f8f9fa;
            padding: 5px;
            border: 1px solid #dee2e6;
            border-radius: 3px;
        """)
        
        self.rectalTempDisplay = QLabel("37.0°C")
        self.rectalTempDisplay.setStyleSheet("""
            font-family: 'Courier New';
            font-size: 16px;
            font-weight: bold;
            color: #28a745;
            background-color: #f8f9fa;
            padding: 5px;
            border: 1px solid #dee2e6;
            border-radius: 3px;
        """)

        self.rectalSetpointDisplay = QLabel("–")
        self.rectalSetpointDisplay.setStyleSheet("""
            font-family: 'Courier New';
            font-size: 14px;
            font-weight: bold;
            color: #495057;
            background-color: #f8f9fa;
            padding: 5px;
            border: 1px dashed #dee2e6;
            border-radius: 3px;
        """)

        self.targetTempDisplay = QLabel("37.0°C")
        self.targetTempDisplay.setStyleSheet("""
            font-family: 'Courier New';
            font-size: 16px;
            font-weight: bold; 
            color: #007bff;
            background-color: #f8f9fa;
            padding: 5px;
            border: 1px solid #dee2e6;
            border-radius: 3px;
        """)

        self.adjustedTargetDisplay = QLabel("–")
        self.adjustedTargetDisplay.setStyleSheet("""
            font-family: 'Courier New';
            font-size: 14px;
            font-weight: bold;
            color: #ff6f00;
            background-color: #fff8e1;
            padding: 5px;
            border: 1px solid #ffe4a1;
            border-radius: 3px;
        """)
        
        self.pidOutputDisplay = QLabel("0.0")
        self.pidOutputDisplay.setStyleSheet("""
            font-family: 'Courier New'; 
            font-size: 16px; 
            font-weight: bold; 
            color: #6f42c1;
            background-color: #f8f9fa;
            padding: 5px;
            border: 1px solid #dee2e6;
            border-radius: 3px;
        """)
        
        self.breathRateDisplay = QLabel("150 BPM")
        self.breathRateDisplay.setStyleSheet("""
            font-family: 'Courier New'; 
            font-size: 16px; 
            font-weight: bold; 
            color: #fd7e14;
            background-color: #f8f9fa;
            padding: 5px;
            border: 1px solid #dee2e6;
            border-radius: 3px;
        """)
        
        data_layout.addWidget(QLabel("🔥 Cooling Plate:"), 0, 0)
        data_layout.addWidget(self.plateTempDisplay, 0, 1)
        data_layout.addWidget(QLabel("🌡️ Rectal Probe:"), 1, 0)
        data_layout.addWidget(self.rectalTempDisplay, 1, 1)
        data_layout.addWidget(QLabel("🎯 Target:"), 2, 0)
        data_layout.addWidget(self.targetTempDisplay, 2, 1)
        data_layout.addWidget(QLabel("📌 Rectal setpoint:"), 3, 0)
        data_layout.addWidget(self.rectalSetpointDisplay, 3, 1)
        data_layout.addWidget(QLabel("🟠 Modified target:"), 4, 0)
        data_layout.addWidget(self.adjustedTargetDisplay, 4, 1)
        data_layout.addWidget(QLabel("⚡ PID Output:"), 5, 0)
        data_layout.addWidget(self.pidOutputDisplay, 5, 1)
        data_layout.addWidget(QLabel("🫁 Breath Rate:"), 6, 0)
        data_layout.addWidget(self.breathRateDisplay, 6, 1)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # System parameters
        params_group = QGroupBox("⚙️ System Parameters")
        params_layout = QFormLayout()

        self.pidParamsLabel = QLabel("Heating: - | Cooling: -")
        self.pidParamsLabel.setStyleSheet("font-family: 'Courier New'; font-size: 11px;")
        self.pidParamsLabel.setWordWrap(True)
        self.pidParamsLabel.setMinimumWidth(260)

        self.maxOutputLabel = QLabel("Unknown")
        self.maxOutputLabel.setStyleSheet("font-family: 'Courier New'; font-size: 11px;")
        self.maxOutputLabel.setWordWrap(True)
        self.maxOutputLabel.setMinimumWidth(260)
        
        self.lastUpdateLabel = QLabel("Never")
        self.lastUpdateLabel.setStyleSheet("font-family: 'Courier New'; font-size: 10px; color: #6c757d;")
        
        params_layout.addRow("Asymmetric PID:", self.pidParamsLabel)
        params_layout.addRow("Max Output:", self.maxOutputLabel)
        params_layout.addRow("Last Update:", self.lastUpdateLabel)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # System utilities now resides beneath parameters
        advanced_group = QGroupBox("System Utilities")
        advanced_layout = QGridLayout()
        advanced_layout.setHorizontalSpacing(12)
        advanced_layout.setVerticalSpacing(8)
        advanced_layout.setColumnStretch(0, 1)
        advanced_layout.setColumnStretch(1, 1)

        self.refreshPidButton = QPushButton("Refresh PID")
        self.refreshPidButton.setMinimumWidth(120)
        self.refreshPidButton.clicked.connect(self.refresh_pid_from_device)

        self.applyBothPidButton = QPushButton("Apply PID")
        self.applyBothPidButton.setMinimumWidth(120)
        self.applyBothPidButton.clicked.connect(self.asymmetric_controls.apply_both_pid)

        self.setMaxOutputButton = QPushButton("Max Output")
        self.setMaxOutputButton.setMinimumWidth(120)
        self.setMaxOutputButton.clicked.connect(self.set_max_output_limit)

        self.saveEEPROMButton = QPushButton("Save EEPROM")
        self.saveEEPROMButton.setMinimumWidth(120)
        self.saveEEPROMButton.clicked.connect(self.save_pid_to_eeprom)

        self.requestStatusButton = QPushButton("Refresh Status")
        self.requestStatusButton.setMinimumWidth(120)
        self.requestStatusButton.clicked.connect(self.request_status)

        self.clearFailsafeButton = QPushButton("Clear FS")
        self.clearFailsafeButton.setMinimumWidth(120)
        self.clearFailsafeButton.clicked.connect(self.clear_failsafe)
        self.clearFailsafeButton.setStyleSheet("background-color: #fd7e14; color: white; font-weight: bold;")

        self.disableBreathCheckBox = QCheckBox("Disable breath-stop check")
        self.disableBreathCheckBox.setToolTip("Ignore 'no_breathing_detected' failsafes (for testing only)")
        self.disableBreathCheckBox.stateChanged.connect(self.toggle_breath_check)

        advanced_layout.addWidget(self.refreshPidButton, 0, 0)
        advanced_layout.addWidget(self.applyBothPidButton, 0, 1)
        advanced_layout.addWidget(self.setMaxOutputButton, 1, 0)
        advanced_layout.addWidget(self.saveEEPROMButton, 1, 1)
        advanced_layout.addWidget(self.requestStatusButton, 2, 0)
        advanced_layout.addWidget(self.clearFailsafeButton, 2, 1)
        advanced_layout.addWidget(self.disableBreathCheckBox, 3, 0, 1, 2)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        layout.addStretch()
        return panel

    def create_monitoring_tab(self):
        """Create monitoring tab with graphs"""
        monitoring_widget = QWidget()
        monitoring_layout = QVBoxLayout()
        monitoring_widget.setLayout(monitoring_layout)
        
        # Graph controls
        controls_layout = QHBoxLayout()
        
        self.testBasicPlotButton = QPushButton("🧪 Test Plot")
        self.testBasicPlotButton.clicked.connect(self.test_basic_plot)
        self.testBasicPlotButton.setStyleSheet("background-color: #e83e8c; color: white; font-weight: bold;")
        
        self.generateTestDataButton = QPushButton("📊 Generate Test Data")
        self.generateTestDataButton.clicked.connect(self.generate_test_data)
        self.generateTestDataButton.setStyleSheet("background-color: #007bff; color: white; font-weight: bold;")
        
        self.clearGraphsButton = QPushButton("🧹 Clear Graphs")
        self.clearGraphsButton.clicked.connect(self.clear_graphs)
        self.clearGraphsButton.setStyleSheet("background-color: #fd7e14; color: white; font-weight: bold;")

        self.resetZoomButton = QPushButton("🔍 Reset zoom")
        self.resetZoomButton.clicked.connect(lambda: hasattr(self, 'graph_widget') and self.graph_widget.reset_zoom())
        self.resetZoomButton.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold;")

        controls_layout.addWidget(self.testBasicPlotButton)
        controls_layout.addWidget(self.generateTestDataButton)
        controls_layout.addWidget(self.clearGraphsButton)
        controls_layout.addWidget(self.resetZoomButton)
        controls_layout.addStretch()
        
        monitoring_layout.addLayout(controls_layout)
        
        # Matplotlib widget
        try:
            self.graph_widget = MatplotlibGraphWidget()
            monitoring_layout.addWidget(self.graph_widget)
            print("✅ Graph widget created")
        except Exception as e:
            print(f"❌ Graph widget error: {e}")
            error_label = QLabel("❌ Graph creation failed")
            error_label.setStyleSheet("background-color: #f8d7da; color: #721c24; padding: 20px;")
            error_label.setAlignment(Qt.AlignCenter)
            monitoring_layout.addWidget(error_label)
        
        self.tab_widget.addTab(monitoring_widget, "📈 Monitoring")

    def create_autotune_tab(self):
        """Create autotune wizard tab"""
        self.autotune_wizard = AutotuneWizardTab(self)
        self.tab_widget.addTab(self.autotune_wizard, "🎯 Autotune")

    def create_profile_tab(self):
        """Create profile tab"""
        profile_widget = QWidget()
        profile_layout = QVBoxLayout()
        profile_widget.setLayout(profile_layout)
        
        # Profile loading
        load_group = QGroupBox("📁 Profile Management")
        load_layout = QHBoxLayout()
        
        self.loadProfileButton = QPushButton("📂 Load Profile")
        self.loadProfileButton.clicked.connect(self.load_profile)
        self.loadProfileButton.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold;")
        
        self.profileFileLabel = QLabel("No profile loaded")
        self.profileFileLabel.setStyleSheet("font-style: italic; color: #6c757d;")
        
        load_layout.addWidget(self.loadProfileButton)
        load_layout.addWidget(self.profileFileLabel)
        load_layout.addStretch()

        load_group.setLayout(load_layout)
        profile_layout.addWidget(load_group)

        preview_group = QGroupBox("🔎 Profile Preview")
        preview_layout = QVBoxLayout()
        self.profilePreviewPlot = pg.PlotWidget()
        self.profilePreviewPlot.addLegend()
        self.profilePreviewPlot.showGrid(x=True, y=True, alpha=0.3)
        self.profilePreviewPlot.setLabel("bottom", "Tid", units="s")
        self.profilePreviewPlot.setLabel("left", "Temperatur", units="°C")
        self.profilePreviewPlot.getPlotItem().getAxis("bottom").enableAutoSIPrefix(False)
        self.profilePreviewPlot.getPlotItem().getAxis("left").enableAutoSIPrefix(False)
        preview_layout.addWidget(self.profilePreviewPlot)
        preview_group.setLayout(preview_layout)
        profile_layout.addWidget(preview_group)
        
        # Profile controls
        control_group = QGroupBox("🎮 Profile Control")
        control_layout = QHBoxLayout()
        
        self.startProfileButton = QPushButton("▶️ Start")
        self.startProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "start"))
        self.startProfileButton.setEnabled(False)
        self.startProfileButton.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        
        self.pauseProfileButton = QPushButton("⏸️ Pause")
        self.pauseProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "pause"))
        self.pauseProfileButton.setEnabled(False)
        self.pauseProfileButton.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold;")
        
        self.resumeProfileButton = QPushButton("▶️ Resume")
        self.resumeProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "resume"))
        self.resumeProfileButton.setEnabled(False)
        self.resumeProfileButton.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold;")

        self.stopProfileButton = QPushButton("⏹️ Stop")
        self.stopProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "stop"))
        self.stopProfileButton.setEnabled(False)
        self.stopProfileButton.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")

        control_layout.addWidget(self.startProfileButton)
        control_layout.addWidget(self.pauseProfileButton)
        control_layout.addWidget(self.resumeProfileButton)
        control_layout.addWidget(self.stopProfileButton)
        
        self.profileStatusLabel = QLabel("Profile: idle")
        self.profileStatusLabel.setStyleSheet("color: #6c757d; font-weight: bold;")
        control_layout.addWidget(self.profileStatusLabel)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        profile_layout.addWidget(control_group)
        
        # Event log
        log_group = QGroupBox("📋 Event Log")
        log_layout = QVBoxLayout()
        
        log_controls = QHBoxLayout()
        
        self.clearLogButton = QPushButton("🧹 Clear")
        self.clearLogButton.clicked.connect(lambda: self.logBox.clear())
        
        self.autoScrollCheckbox = QCheckBox("📜 Auto-scroll")
        self.autoScrollCheckbox.setChecked(True)
        
        log_controls.addWidget(self.clearLogButton)
        log_controls.addWidget(self.autoScrollCheckbox)
        log_controls.addStretch()
        
        self.logBox = QTextEdit()
        self.logBox.setReadOnly(True)
        self.logBox.setMaximumHeight(200)
        self.logBox.setFont(QFont("Courier New", 9))
        self.logBox.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        log_layout.addLayout(log_controls)
        log_layout.addWidget(self.logBox)
        log_group.setLayout(log_layout)
        
        profile_layout.addWidget(log_group)
        profile_layout.addStretch()

        self.tab_widget.addTab(profile_widget, "📄 Profile")
        self._update_profile_button_states()

    def create_serial_monitor_tab(self):
        """Create serial monitor tab to display raw TX/RX lines."""

        monitor_widget = QWidget()
        monitor_layout = QVBoxLayout()
        monitor_widget.setLayout(monitor_layout)

        controls_layout = QHBoxLayout()
        self.serialMonitorClearButton = QPushButton("🧹 Clear")
        self.serialMonitorClearButton.clicked.connect(self.clear_serial_monitor)
        self.serialMonitorAutoScroll = QCheckBox("📜 Auto-scroll")
        self.serialMonitorAutoScroll.setChecked(True)
        controls_layout.addWidget(self.serialMonitorClearButton)
        controls_layout.addWidget(self.serialMonitorAutoScroll)
        controls_layout.addStretch()

        tx_group = QGroupBox("TX → Arduino")
        tx_layout = QVBoxLayout()
        self.serialMonitorTxLog = QTextEdit()
        self.serialMonitorTxLog.setReadOnly(True)
        self.serialMonitorTxLog.setFont(QFont("Courier New", 9))
        self.serialMonitorTxLog.setStyleSheet(
            """
            QTextEdit {
                background-color: #0b132b;
                color: #0dcaf0;
                border: 1px solid #1c2541;
                border-radius: 6px;
                padding: 8px;
            }
        """
        )
        tx_layout.addWidget(self.serialMonitorTxLog)
        tx_group.setLayout(tx_layout)

        rx_group = QGroupBox("RX ← Arduino")
        rx_layout = QVBoxLayout()
        self.serialMonitorRxLog = QTextEdit()
        self.serialMonitorRxLog.setReadOnly(True)
        self.serialMonitorRxLog.setFont(QFont("Courier New", 9))
        self.serialMonitorRxLog.setStyleSheet(
            """
            QTextEdit {
                background-color: #0b132b;
                color: #51cf66;
                border: 1px solid #1c2541;
                border-radius: 6px;
                padding: 8px;
            }
        """
        )
        rx_layout.addWidget(self.serialMonitorRxLog)
        rx_group.setLayout(rx_layout)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(tx_group)
        splitter.addWidget(rx_group)
        splitter.setSizes([200, 200])

        monitor_layout.addLayout(controls_layout)
        monitor_layout.addWidget(splitter)

        self.tab_widget.addTab(monitor_widget, "🛰️ Serial Monitor")

    def create_calibration_tab(self):
        """Create calibration tab and hook command buttons."""

        self.calibration_tab = CalibrationTab(self)
        self.tab_widget.addTab(self.calibration_tab, "📐 Calibration")

    def init_managers(self):
        """Initialize managers"""
        try:
            # Serial manager
            self.serial_manager = SerialManager()
            self.serial_manager.data_received.connect(self.process_incoming_data)
            self.serial_manager.raw_line_received.connect(
                lambda line: self.on_serial_line("RX", line)
            )
            self.serial_manager.raw_line_sent.connect(
                lambda line: self.on_serial_line("TX", line)
            )
            self.serial_manager.failsafe_triggered.connect(self.on_pc_failsafe_triggered)
            print("✅ SerialManager initialized")

            # Event logger
            self.event_logger = EventLogger("gui_v3_events")
            print("✅ EventLogger initialized")
            
            # Profile loader
            self.profile_loader = ProfileLoader(event_logger=self.event_logger)
            print("✅ ProfileLoader initialized")

            # Status timer
            self.status_timer = QTimer()
            self.status_timer.timeout.connect(self.request_status)
            # 1s cadence keeps graphs/data responsive without noticeable CPU load.
            self.status_timer.start(1000)
            
            # Sync timer
            self.sync_timer = QTimer()
            self.sync_timer.setSingleShot(True)
            self.sync_timer.timeout.connect(self.initial_sync)
            
            # Populate ports
            self.refresh_ports()
            
            print("✅ All managers initialized")

        except Exception as e:
            print(f"❌ Manager initialization error: {e}")

    # ====== CORE FUNCTIONALITY ======

    def _start_data_logger(self):
        """Start a new data logger for experiment runs."""
        if not self.connection_established:
            return

        try:
            if self.data_logger is not None:
                try:
                    self.data_logger.close()
                except Exception:
                    pass

            metadata = {
                "port": getattr(self.serial_manager, "port", "unknown"),
                "session_start": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.data_logger = Logger("gui_experiment", metadata=metadata)
            self.log("📝 Data logger started", "info")
        except Exception as exc:
            self.data_logger = None
            self.log(f"❌ Could not start data logger: {exc}", "error")

    def _stop_data_logger(self):
        """Close and clear the active data logger."""
        if self.data_logger is None:
            return

        try:
            self.data_logger.close()
            self.log("🛑 Data logger stopped", "info")
        except Exception as exc:
            self.log(f"⚠️ Error while stopping data logger: {exc}", "warning")
        finally:
            self.data_logger = None

    @staticmethod
    def _has_sensor_payload(data: Dict[str, Any]) -> bool:
        sensor_keys = {"cooling_plate_temp", "anal_probe_temp", "pid_output", "breath_freq_bpm"}
        return any(key in data for key in sensor_keys)

    def send_and_log_cmd(self, action: str, state: str) -> bool:
        """Send command with error handling"""
        try:
            if not self.connection_established:
                self.log("❌ Not connected", "error")
                return False

            if action == "profile" and state == "start":
                if not self.profile_steps:
                    self.log("⚠️ Load and send a profile before starting.", "warning")
                    return False
                try:
                    self.serial_manager.sendSET("profile_data", self.profile_steps)
                    self.profile_upload_pending = True
                    self._update_profile_button_states()
                except Exception as exc:
                    self.log(f"❌ Failed to send profile: {exc}", "error")
                    return False

            self.serial_manager.sendCMD(action, state)
            self.event_logger.log_event(f"CMD: {action} → {state}")
            self.log(f"📡 Sent: {action} = {state}", "command")

            if action == "pid" and state == "start":
                self._start_data_logger()
            elif action == "pid" and state == "stop":
                self._stop_data_logger()

            return True

        except Exception as e:
            self.log(f"❌ Command error: {e}", "error")
            return False

    def request_equilibrium_estimate(self):
        """Trigger an explicit equilibrium measurement on the controller."""
        if self.send_and_log_cmd("equilibrium", "estimate"):
            self.equilibrium_estimating = True
            self.equilibriumStateLabel.setText("Equilibrium: estimating…")
            self.equilibriumStateLabel.setStyleSheet(
                "color: #b07d11; font-weight: bold;"
            )

    def toggle_equilibrium_compensation(self, state):
        """Enable/disable equilibrium compensation flag on Arduino."""
        enable = self.equilibriumCompCheckbox.isChecked()
        if not self.connection_established:
            with QSignalBlocker(self.equilibriumCompCheckbox):
                self.equilibriumCompCheckbox.setChecked(self.equilibrium_comp_enabled)
            self.log("❌ Not connected", "error")
            return

        try:
            self.serial_manager.sendSET("equilibrium_compensation", bool(enable))
            self.event_logger.log_event(
                f"SET: equilibrium_compensation → {enable}")
            msg = "🧭 Equilibrium compensation enabled" if enable else \
                  "🧭 Equilibrium compensation disabled"
            self.log(msg, "info")
        except Exception as exc:
            self.log(f"❌ Could not update equilibrium compensation: {exc}", "error")

    def process_incoming_data(self, data: Dict[str, Any]):
        """Process incoming data from Arduino"""
        if not data:
            return

        try:
            self.data_update_count += 1

            if data.get("type") == "calibration_table" and hasattr(self, "calibration_tab"):
                self.calibration_tab.update_table(data)
                self.log("📐 Mottok kalibreringstabell", "info")
                return

            if (
                self.disable_breath_check
                and data.get("failsafe_reason") == "no_breathing_detected"
            ):
                if not self.breath_suppression_notified:
                    self.log("⏸️ Ignoring 'no_breathing_detected' failsafe (test mode)", "warning")
                    self.event_logger.log_event("EVENT: breath_check_suppressed")
                    self.breath_suppression_notified = True
                data = dict(data)
                data["failsafe_active"] = False
            else:
                self.breath_suppression_notified = False

            if "failsafe_active" in data:
                self._apply_failsafe_state(
                    bool(data.get("failsafe_active", False)),
                    data.get("failsafe_reason", "Unknown"),
                    log_event=True,
                )

            has_sensor_data = self._has_sensor_payload(data)
            if has_sensor_data and self.connection_established:
                if self.data_logger is None:
                    self._start_data_logger()
                if self.data_logger is not None:
                    self.data_logger.log_data(data)

            # Update live displays
            self.update_live_displays(data)

            # Oppdater kalibreringsfeltene når status inneholder rå/kalibrerte verdier
            plate_raw = data.get("cooling_plate_raw", data.get("cooling_plate_temp_raw"))
            plate_cal = data.get("cooling_plate_temp")
            rectal_raw = data.get("rectal_raw", data.get("anal_probe_temp_raw"))
            rectal_cal = data.get("rectal_temp", data.get("anal_probe_temp"))

            if hasattr(self, "calibration_tab"):
                self.calibration_tab.update_raw_values(
                    plate_raw,
                    plate_cal,
                    rectal_raw,
                    rectal_cal,
                )

            # Update PID parameters
            self.update_pid_displays(data)
            
            # Update status indicators
            self.update_status_indicators(data)
            self.last_status_data = dict(data)

            # ============================================================================
            # 6. ADD THIS LINE TO UPDATE ASYMMETRIC CONTROLS
            # ============================================================================
            if hasattr(self, 'asymmetric_controls'):
                self.asymmetric_controls.update_status(data)

            if hasattr(self, 'autotune_wizard'):
                self.autotune_wizard.receive_data(data)

            # Update graphs
            if self.connection_established and hasattr(self, 'graph_widget'):
                self.update_live_graph_data(data)
            
            # Handle events
            self.handle_events(data)
            
            # Update timestamp
            self.lastUpdateLabel.setText(time.strftime("%H:%M:%S"))
                
        except Exception as e:
            self.log(f"❌ Data processing error: {e}", "error")

    def _apply_failsafe_state(self, active: bool, reason: str = "Unknown", *, log_event: bool = False):
        """Update UI + logs when failsafe state changes."""

        reason_text = reason or "Unknown"
        previous_state = self.failsafe_active
        self.failsafe_active = active
        self.last_failsafe_reason = reason_text

        if active:
            self.failsafeIndicator.setText(f"🔴 FAILSAFE: {reason_text}")
            self.failsafeIndicator.setStyleSheet("color: #dc3545; font-weight: bold;")
            if hasattr(self, "emergencyStateValue"):
                self.emergencyStateValue.setText(f"🚨 {reason_text}")
                self.emergencyStateValue.setStyleSheet("font-weight: bold; color: #dc3545;")
            if log_event and not previous_state:
                self.event_logger.log_event(f"EVENT: FAILSAFE_TRIGGERED ({reason_text})")
                if self.data_logger is not None:
                    self.data_logger.log_event(f"FAILSAFE_TRIGGERED ({reason_text})")
                self.log(f"🚨 FAILSAFE ACTIVE: {reason_text}", "error")
                self.log_emergency_event(f"FAILSAFE TRIGGERED → {reason_text}")
        else:
            self.failsafeIndicator.setText("🟢 Safe")
            self.failsafeIndicator.setStyleSheet("color: #28a745; font-weight: bold;")
            if hasattr(self, "emergencyStateValue"):
                self.emergencyStateValue.setText("✅ Clear")
                self.emergencyStateValue.setStyleSheet("font-weight: bold; color: #28a745;")
            self.pc_failsafe_dialog_shown = False
            self.panic_active = False
            if log_event and previous_state:
                self.event_logger.log_event("EVENT: FAILSAFE_CLEARED")
                if self.data_logger is not None:
                    self.data_logger.log_event("FAILSAFE_CLEARED")
                self.log("✅ Failsafe cleared", "info")
                self.log_emergency_event("FAILSAFE CLEARED")

    def log_emergency_event(self, message: str):
        """Append a timestamped emergency/failsafe event to the control tab log."""

        try:
            timestamp = time.strftime("%H:%M:%S")
            entry = f"[{timestamp}] {message}"
            self.emergency_event_history.append(entry)
            # Keep the log to the most recent 50 entries
            if len(self.emergency_event_history) > 50:
                self.emergency_event_history = self.emergency_event_history[-50:]

            if (
                hasattr(self, "asymmetric_controls")
                and hasattr(self.asymmetric_controls, "emergencyEventList")
            ):
                self.asymmetric_controls.emergencyEventList.clear()
                self.asymmetric_controls.emergencyEventList.addItems(
                    self.emergency_event_history
                )
                self.asymmetric_controls.emergencyEventList.scrollToBottom()
        except Exception as exc:
            print(f"⚠️ Emergency log error: {exc}")

    def clear_emergency_log(self):
        """Clear the in-memory and on-screen emergency event log."""

        self.emergency_event_history.clear()
        if (
            hasattr(self, "asymmetric_controls")
            and hasattr(self.asymmetric_controls, "emergencyEventList")
        ):
            self.asymmetric_controls.emergencyEventList.clear()

    def on_serial_line(self, direction: str, line: str):
        """Append raw TX/RX serial lines to the Serial Monitor tab."""

        try:
            if not (
                hasattr(self, "serialMonitorTxLog")
                and hasattr(self, "serialMonitorRxLog")
            ):
                return

            direction = direction.upper()
            timestamp = time.strftime("%H:%M:%S")
            formatted = f"[{timestamp}] {direction}: {line}"

            if direction == "TX":
                log_list = self.serial_monitor_tx_lines
                widget = self.serialMonitorTxLog
            else:
                log_list = self.serial_monitor_rx_lines
                widget = self.serialMonitorRxLog

            log_list.append(formatted)
            if len(log_list) > self.serial_monitor_max_lines:
                log_list[:] = log_list[-self.serial_monitor_max_lines :]

            scrollbar = widget.verticalScrollBar()
            prev_value = scrollbar.value()
            prev_max = scrollbar.maximum()

            widget.setPlainText("\n".join(log_list))
            if self.serialMonitorAutoScroll.isChecked():
                widget.moveCursor(QTextCursor.End)
            else:
                if prev_max != scrollbar.maximum():
                    delta = scrollbar.maximum() - prev_max
                    scrollbar.setValue(max(0, prev_value + delta))
                else:
                    scrollbar.setValue(prev_value)

        except Exception as e:
            print(f"Serial monitor error: {e}")

    def clear_serial_monitor(self):
        """Clear Serial Monitor history and display."""

        self.serial_monitor_tx_lines.clear()
        self.serial_monitor_rx_lines.clear()
        if hasattr(self, "serialMonitorTxLog"):
            self.serialMonitorTxLog.clear()
        if hasattr(self, "serialMonitorRxLog"):
            self.serialMonitorRxLog.clear()

    def on_pc_failsafe_triggered(self):
        """Handle PC-side failsafe activation in the GUI thread."""

        try:
            self._apply_failsafe_state(True, "pc_watchdog", log_event=True)

            if not self.pc_failsafe_dialog_shown:
                QMessageBox.warning(
                    self,
                    "Failsafe triggered",
                    "PC watchdog timeout detected. System moved to failsafe.",
                )
                self.pc_failsafe_dialog_shown = True

        except Exception as e:
            print(f"Failsafe handler error: {e}")

    def update_live_displays(self, data: Dict[str, Any]):
        """Update live data displays"""
        try:
            if "cooling_plate_temp" in data:
                temp = float(data["cooling_plate_temp"])
                self.plateTempDisplay.setText(f"{temp:.2f}°C")
                self.current_plate_temp = temp

            if "anal_probe_temp" in data:
                temp = float(data["anal_probe_temp"])
                self.rectalTempDisplay.setText(f"{temp:.2f}°C")
            if "rectal_temp" in data:
                temp = float(data["rectal_temp"])
                self.rectalTempDisplay.setText(f"{temp:.2f}°C")

            rectal_setpoint = self._extract_rectal_setpoint(data)
            if rectal_setpoint is not None:
                self.rectalSetpointDisplay.setText(f"{rectal_setpoint:.2f}°C")
            else:
                self.rectalSetpointDisplay.setText("–")

            if "pid_output" in data:
                output = float(data["pid_output"])
                self.pidOutputDisplay.setText(f"{output:.1f}")

            if "plate_target_active" in data:
                target = float(data["plate_target_active"])
                self.targetTempDisplay.setText(f"{target:.2f}°C")
                self.current_target_temp = target

                adjusted_target = self._extract_adjusted_plate_target(
                    data, target, rectal_setpoint
                )
                if adjusted_target is not None:
                    self.adjustedTargetDisplay.setText(f"{adjusted_target:.2f}°C")
                else:
                    self.adjustedTargetDisplay.setText("–")

            if "breath_freq_bpm" in data:
                breath = float(data["breath_freq_bpm"])
                self.breathRateDisplay.setText(f"{breath:.0f} BPM")

        except (ValueError, KeyError) as e:
            print(f"Display update error: {e}")

    def update_pid_displays(self, data: Dict[str, Any]):
        """Update PID parameter displays"""
        try:
            heating_present = all(
                key in data for key in ["pid_heating_kp", "pid_heating_ki", "pid_heating_kd"]
            )
            cooling_present = all(
                key in data for key in ["pid_cooling_kp", "pid_cooling_ki", "pid_cooling_kd"]
            )

            if heating_present and cooling_present:
                hk = float(data["pid_heating_kp"])
                hi = float(data["pid_heating_ki"])
                hd = float(data["pid_heating_kd"])
                ck = float(data["pid_cooling_kp"])
                ci = float(data["pid_cooling_ki"])
                cd = float(data["pid_cooling_kd"])

                self.pidParamsLabel.setText(
                    "Heating → "
                    f"Kp={hk:.3f}, Ki={hi:.3f}, Kd={hd:.3f}\n"
                    "Cooling → "
                    f"Kp={ck:.3f}, Ki={ci:.3f}, Kd={cd:.3f}"
                )

            if "pid_heating_limit" in data or "pid_cooling_limit" in data:
                heat_limit = float(data.get("pid_heating_limit", 0.0))
                cool_limit = float(data.get("pid_cooling_limit", 0.0))
                self.last_heating_limit = heat_limit
                self.last_cooling_limit = cool_limit
                self.maxOutputLabel.setText(
                    f"Heating limit: {heat_limit:.1f}%\nCooling limit: {cool_limit:.1f}%"
                )
            elif "pid_max_output" in data:
                max_output = float(data["pid_max_output"])
                self.last_heating_limit = max_output
                self.last_cooling_limit = max_output
                self.maxOutputLabel.setText(
                    f"Heating limit: {max_output:.1f}%\nCooling limit: {max_output:.1f}%"
                )

        except (ValueError, KeyError) as e:
            print(f"PID display error: {e}")

    def update_status_indicators(self, data: Dict[str, Any]):
        """Update status indicators"""
        try:
            mode_value = None
            if "pid_mode" in data:
                mode_value = str(data["pid_mode"])
                self.pid_mode = mode_value

            # PID status
            if "pid_output" in data:
                output = abs(float(data["pid_output"]))
                pid_active = output > 0.1
                if mode_value is None and self.pid_mode is not None:
                    mode_value = self.pid_mode

                if mode_value:
                    lowered = mode_value.lower()
                    if lowered in {"off", "stopped", "idle"}:
                        pid_active = False
                    else:
                        pid_active = True

                self.pid_running = pid_active

                if pid_active:
                    self.pidStatusIndicator.setText("🟢 PID On")
                    self.pidStatusIndicator.setStyleSheet("color: #28a745; font-weight: bold;")
                else:
                    self.pidStatusIndicator.setText("⚫ PID Off")
                    self.pidStatusIndicator.setStyleSheet("color: #6c757d; font-weight: bold;")

            if "cooling_mode" in data and hasattr(self, "regulationModeValue"):
                mode_text = "Cooling" if data.get("cooling_mode") else "Heating"
                self.regulationModeValue.setText(mode_text)
                color = "#0d6efd" if data.get("cooling_mode") else "#e55353"
                self.regulationModeValue.setStyleSheet(f"font-weight: bold; color: {color};")

            if "temperature_rate" in data and hasattr(self, "temperatureRateValue"):
                try:
                    rate = float(data.get("temperature_rate", 0.0))
                    self.temperatureRateValue.setText(f"{rate:.3f} °C/s")
                except (TypeError, ValueError):
                    self.temperatureRateValue.setText("-- °C/s")

            if "equilibrium_valid" in data:
                valid = bool(data.get("equilibrium_valid", False))
                if valid and "equilibrium_temp" in data:
                    temp = float(data["equilibrium_temp"])
                    self.equilibriumLabel.setText(f"Equilibrium: {temp:.2f}°C")
                    self.equilibriumLabel.setStyleSheet("color: #1e7e34; font-weight: bold;")
                    if (not self.last_equilibrium_valid) or (
                        self.last_equilibrium_temp is None or abs(self.last_equilibrium_temp - temp) > 0.05
                    ):
                        self.log(f"♒︎ Nytt equilibrium estimert: {temp:.2f}°C", "info")
                    self.last_equilibrium_temp = temp
                    self.last_equilibrium_valid = True
                else:
                    self.equilibriumLabel.setText("Equilibrium: (måles)")
                    self.equilibriumLabel.setStyleSheet("color: #b07d11; font-weight: bold;")
                    self.last_equilibrium_valid = False

            if "equilibrium_estimating" in data:
                self.equilibrium_estimating = bool(data.get("equilibrium_estimating", False))

            if "equilibrium_compensation_active" in data and hasattr(self, "equilibriumCompCheckbox"):
                enabled = bool(data.get("equilibrium_compensation_active", False))
                self.equilibrium_comp_enabled = enabled
                with QSignalBlocker(self.equilibriumCompCheckbox):
                    self.equilibriumCompCheckbox.setChecked(enabled)

            if hasattr(self, "equilibriumStateLabel"):
                if self.equilibrium_estimating:
                    self.equilibriumStateLabel.setText("Equilibrium: estimating…")
                    self.equilibriumStateLabel.setStyleSheet(
                        "color: #b07d11; font-weight: bold;"
                    )
                    if not self.last_equilibrium_valid:
                        self.equilibriumLabel.setText("Equilibrium: (måles)")
                        self.equilibriumLabel.setStyleSheet(
                            "color: #b07d11; font-weight: bold;"
                        )
                elif self.last_equilibrium_valid and self.last_equilibrium_temp is not None:
                    self.equilibriumStateLabel.setText("Equilibrium: ready")
                    self.equilibriumStateLabel.setStyleSheet(
                        "color: #1e7e34; font-weight: bold;"
                    )
                else:
                    self.equilibriumStateLabel.setText("Equilibrium: idle")
                    self.equilibriumStateLabel.setStyleSheet(
                        "color: #6c757d; font-weight: bold;"
                    )

            profile_state_updated = False
            if "profile_active" in data:
                self.profile_active = bool(data["profile_active"])
                profile_state_updated = True
            if "profile_paused" in data:
                self.profile_paused = bool(data["profile_paused"])
                profile_state_updated = True

            if profile_state_updated:
                if self.profile_active:
                    if self.profile_run_start_time is None:
                        self._mark_profile_started()
                    if self.profile_paused:
                        self._mark_profile_paused()
                    else:
                        self._mark_profile_resumed()
                    if hasattr(self, "profileStatusLabel"):
                        status_text = "Profile: running"
                        if self.profile_paused:
                            status_text = "Profile: paused"

                        step_info = ""
                        if "profile_step_index" in data or "profile_step" in data:
                            try:
                                step_num = int(
                                    data.get(
                                        "profile_step_index",
                                        data.get("profile_step", 0)
                                    )
                                )
                                step_info = f" | Step {step_num}"
                            except (TypeError, ValueError):
                                step_info = ""

                        remaining_info = ""
                        if "profile_remaining_time" in data:
                            try:
                                remaining_ms = float(data.get("profile_remaining_time", 0.0))
                                remaining_sec = max(0, remaining_ms / 1000.0)
                                remaining_info = f" | {remaining_sec:.0f}s left"
                            except (TypeError, ValueError):
                                remaining_info = ""

                        self.profileStatusLabel.setText(status_text + step_info + remaining_info)
                        self.profileStatusLabel.setStyleSheet("color: #0d6efd; font-weight: bold;")
                else:
                    self._mark_profile_stopped()
                    if hasattr(self, "profileStatusLabel"):
                        self.profileStatusLabel.setText("Profile: idle")
                        self.profileStatusLabel.setStyleSheet("color: #6c757d; font-weight: bold;")
                self._update_profile_button_states()

        except (ValueError, KeyError) as e:
            print(f"Status indicator error: {e}")

    def update_live_graph_data(self, data: Dict[str, Any]):
        """Update live graph data"""
        try:
            # Only update if we have temperature data
            if not ("cooling_plate_temp" in data and "anal_probe_temp" in data):
                return
            
            # Initialize timing
            if not self.start_time:
                self.start_time = time.time()
            
            # Calculate elapsed time
            elapsed = time.time() - self.start_time
            
            # Add new data
            self.graph_data["time"].append(elapsed)
            self.graph_data["plate_temp"].append(float(data["cooling_plate_temp"]))
            self.graph_data["rectal_temp"].append(float(data["anal_probe_temp"]))
            self.graph_data["pid_output"].append(float(data.get("pid_output", 0)))
            self.graph_data["breath_rate"].append(float(data.get("breath_freq_bpm", 0)))

            base_target = float(data.get("plate_target_active", 37))
            self.graph_data["target_temp"].append(base_target)

            rectal_setpoint = self._extract_rectal_setpoint(data)
            if rectal_setpoint is None:
                self.graph_data["rectal_target_temp"].append(float("nan"))
            else:
                self.graph_data["rectal_target_temp"].append(float(rectal_setpoint))

            adjusted_target = self._extract_adjusted_plate_target(
                data, base_target, rectal_setpoint
            )
            if adjusted_target is None:
                self.graph_data["adjusted_target_temp"].append(float("nan"))
            else:
                self.graph_data["adjusted_target_temp"].append(float(adjusted_target))
            
            # Trim data
            for key in self.graph_data:
                if len(self.graph_data[key]) > self.max_graph_points:
                    self.graph_data[key] = self.graph_data[key][-self.max_graph_points:]
            
            # Update graphs
            if hasattr(self, 'graph_widget'):
                success = self.graph_widget.update_graphs(self.graph_data)
                if success:
                    self.graph_update_count += 1
                    
        except (ValueError, KeyError) as e:
            print(f"Graph update error: {e}")

    def handle_events(self, data: Dict[str, Any]):
        """Handle events and responses"""
        try:
            if "event" in data:
                event_msg = str(data["event"])
                self.log(f"📢 EVENT: {event_msg}", "info")
                self.event_logger.log_event(event_msg)

                event_lower = event_msg.lower()
                if "profile" in event_lower:
                    if "started" in event_lower:
                        self._mark_profile_started()
                    elif any(
                        keyword in event_lower
                        for keyword in ("completed", "stopped", "finished", "aborted")
                    ):
                        self._mark_profile_stopped()
                    elif "paused" in event_lower:
                        self._mark_profile_paused()
                    elif "resumed" in event_lower:
                        self._mark_profile_resumed()

            if "response" in data:
                response_msg = str(data["response"])
                self.log(f"📥 RESPONSE: {response_msg}", "info")

                response_lower = response_msg.lower()

                if "profile" in response_lower:
                    if "started" in response_lower:
                        self._mark_profile_started()
                    elif any(
                        keyword in response_lower
                        for keyword in ("completed", "stopped", "finished", "aborted")
                    ):
                        self._mark_profile_stopped()
                    elif "paused" in response_lower:
                        self._mark_profile_paused()
                    elif "resumed" in response_lower:
                        self._mark_profile_resumed()

                if self.profile_upload_pending and response_lower.startswith("profile"):
                    self.profile_upload_pending = False
                    if any(
                        keyword in response_lower
                        for keyword in ("loaded", "accepted", "ready", "stored")
                    ):
                        self.profile_ready = True
                        self.profile_active = False
                        self.profile_paused = False
                        self._update_profile_button_states()
                        success_message = "Profile upload confirmed by controller"
                        self.log(f"✅ {success_message}", "success")
                        self.event_logger.log_event(success_message)
                    else:
                        self.profile_ready = False
                        self.profile_active = False
                        self.profile_paused = False
                        self._update_profile_button_states()
                        failure_message = f"Profile upload failed: {response_msg}"
                        self.log(f"❌ {failure_message}", "error")
                        self.event_logger.log_event(failure_message)
                        QMessageBox.warning(self, "Profile Upload Failed", response_msg)

                elif (
                    self.profile_upload_pending
                    and any(keyword in response_lower for keyword in ("error", "invalid", "failed"))
                ):
                    self.profile_upload_pending = False
                    self.profile_ready = False
                    self.profile_active = False
                    self.profile_paused = False
                    self._update_profile_button_states()
                    failure_message = f"Profile upload failed: {response_msg}"
                    self.log(f"❌ {failure_message}", "error")
                    self.event_logger.log_event(failure_message)
                    QMessageBox.warning(self, "Profile Upload Failed", response_msg)

                if response_lower == "profile started":
                    self.profile_ready = True
                    self.profile_active = True
                    self.profile_paused = False
                    self._update_profile_button_states()
                elif response_lower == "profile paused":
                    self.profile_active = True
                    self.profile_paused = True
                    self._update_profile_button_states()
                elif response_lower in ("profile resumed", "profile continued"):
                    self.profile_active = True
                    self.profile_paused = False
                    self._update_profile_button_states()
                elif response_lower == "profile stopped":
                    self.profile_active = False
                    self.profile_paused = False
                    self._update_profile_button_states()

            # Handle autotune results
            if "autotune_results" in data:
                self.handle_autotune_results(data["autotune_results"])

        except Exception as e:
            print(f"Event handling error: {e}")

    def handle_autotune_results(self, results: Dict[str, Any]):
        """Handle autotune completion"""
        try:
            normalized: Dict[str, Any] = {}
            if hasattr(self, "autotune_wizard"):
                self.autotune_wizard.display_results(results)
                normalized = getattr(
                    self.autotune_wizard,
                    "_latest_results_payload",
                    {},
                )
            else:
                normalized = results

            kp = normalized.get("kp")
            ki = normalized.get("ki")
            kd = normalized.get("kd")
            cool_kp = normalized.get("cooling_kp")
            cool_ki = normalized.get("cooling_ki")
            cool_kd = normalized.get("cooling_kd")

            if kp is None or ki is None or kd is None:
                missing = [
                    name
                    for name, value in (("Kp", kp), ("Ki", ki), ("Kd", kd))
                    if value is None
                ]
                self.log(
                    "⚠️ Autotune-resultatet mangler PID-komponenter: " + ", ".join(missing),
                    "warning",
                )
                return

            kp = float(kp)
            ki = float(ki)
            kd = float(kd)

            cooling_available = (
                cool_kp is not None and cool_ki is not None and cool_kd is not None
            )
            if cooling_available:
                cool_kp = float(cool_kp)
                cool_ki = float(cool_ki)
                cool_kd = float(cool_kd)

            if hasattr(self, "asymmetric_controls"):
                self.asymmetric_controls.kp_heating_input.setText(f"{kp:.3f}")
                self.asymmetric_controls.ki_heating_input.setText(f"{ki:.3f}")
                self.asymmetric_controls.kd_heating_input.setText(f"{kd:.3f}")
                if cooling_available:
                    self.asymmetric_controls.kp_cooling_input.setText(f"{cool_kp:.3f}")
                    self.asymmetric_controls.ki_cooling_input.setText(f"{cool_ki:.3f}")
                    self.asymmetric_controls.kd_cooling_input.setText(f"{cool_kd:.3f}")

            message_lines = [
                "New heating PID parameters:",
                f"Kp: {kp:.3f}",
                f"Ki: {ki:.3f}",
                f"Kd: {kd:.3f}",
            ]
            if cooling_available:
                message_lines.extend(
                    [
                        "",
                        "Cooling PID parameters:",
                        f"Kp: {cool_kp:.3f}",
                        f"Ki: {cool_ki:.3f}",
                        f"Kd: {cool_kd:.3f}",
                    ]
                )

            message_lines.append("\nReview and apply via the PID controls if needed.")

            QMessageBox.information(
                self,
                "🎯 Autotune Complete",
                "\n".join(message_lines),
            )

            self.log(
                f"🎯 Autotune: Kp={kp:.3f}, Ki={ki:.3f}, Kd={kd:.3f}",
                "success",
            )
            if cooling_available:
                self.log(
                    f"❄️ Autotune (cooling): Kp={cool_kp:.3f}, Ki={cool_ki:.3f}, Kd={cool_kd:.3f}",
                    "success",
                )

        except (ValueError, KeyError) as e:
            print(f"Autotune results error: {e}")

    def send_target_temperature(self, value: float, *, source: str = "", silent: bool = False) -> bool:
        """Send new plate target temperature with consistent logging."""
        try:
            if not (-10.0 <= value <= 50.0):
                raise ValueError("Temperature must be -10°C to 50°C")

            if not self.connection_established:
                if not silent:
                    self.log("❌ Not connected", "error")
                return False

            self.serial_manager.sendSET("target_temp", value)
            event_msg = f"SET: target_temp → {value:.2f}°C"
            if source:
                event_msg += f" ({source})"
            self.event_logger.log_event(event_msg)

            message = f"✅ Target set: {value:.2f}°C"
            if source:
                message += f" ({source})"
            self.log(message, "info" if silent else "success")
            return True

        except ValueError as e:
            if not silent:
                QMessageBox.warning(self, "Invalid Input", f"Temperature error: {e}")
            self.log(f"❌ Target set error: {e}", "error")
        except Exception as e:
            self.log(f"❌ Target set error: {e}", "error")

        return False

    def set_manual_setpoint(self):
        """Set target temperature"""
        try:
            value = float(self.setpointInput.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Temperature error: could not parse value")
            self.log("❌ Invalid temperature: could not parse value", "error")
            return

        self.send_target_temperature(value)

    def add_calibration_point(self):
        """Forwarded for compatibility to the calibration tab."""
        if hasattr(self, "calibration_tab"):
            self.calibration_tab._add_calibration_point()

    def commit_calibration(self):
        """Forwarded for compatibility to the calibration tab."""
        if hasattr(self, "calibration_tab"):
            self.calibration_tab._commit_calibration()

    def set_max_output_limit(self):
        """Set max output limit"""
        try:
            heating_default = max(0.0, self.last_heating_limit)
            cooling_default = max(0.0, self.last_cooling_limit)

            heating, cooling, ok = MaxOutputDialog.get_limits(
                self,
                heating_default,
                cooling_default,
            )

            if ok:
                if not self.connection_established:
                    self.log("❌ Not connected", "error")
                    return

                payload = {"heating": heating, "cooling": cooling}
                if self.send_asymmetric_command("set_output_limits", payload):
                    self.last_heating_limit = heating
                    self.last_cooling_limit = cooling
                    self.maxOutputLabel.setText(
                        f"Heating limit: {heating:.1f}%\nCooling limit: {cooling:.1f}%"
                    )
                    self.log(
                        "⚙️ Output limits → "
                        f"Heating {heating:.1f}% | Cooling {cooling:.1f}%",
                        "command",
                    )

        except Exception as e:
            self.log(f"❌ Max output error: {e}", "error")

    def refresh_pid_from_device(self):
        """Request the latest PID parameters and status from the controller"""
        try:
            if not self.connection_established:
                self.log("❌ Not connected", "error")
                return

            self.serial_manager.sendCMD("get", "pid_params")
            self.event_logger.log_event("CMD: get pid_params")
            self.log("Requested asymmetric PID parameters", "command")

            QTimer.singleShot(250, lambda: self.serial_manager.sendCMD("get", "status"))

        except Exception as e:
            self.log(f"❌ PID refresh error: {e}", "error")

    def save_pid_to_eeprom(self):
        """Save to EEPROM"""
        try:
            if not self.connection_established:
                self.log("❌ Not connected", "error")
                return
                
            self.serial_manager.sendCMD("save_eeprom", "")
            self.event_logger.log_event("CMD: save_eeprom")
            self.log("💾 EEPROM saved", "success")
            
        except Exception as e:
            self.log(f"❌ EEPROM error: {e}", "error")

    def trigger_panic(self):
        """Emergency panic"""
        try:
            reply = QMessageBox.question(
                self, "🚨 EMERGENCY PANIC", 
                "Trigger emergency panic?\n\nThis stops all operations!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if not self.connection_established:
                    self.log("❌ Not connected", "error")
                    return

                self.serial_manager.sendCMD("panic", "")
                self.event_logger.log_event("EVENT: PANIC_TRIGGERED")
                if self.data_logger is not None:
                    self.data_logger.log_event("PANIC_TRIGGERED")
                self.panic_active = True
                self._apply_failsafe_state(True, "gui_panic_triggered", log_event=True)
                self.log_emergency_event("PANIC TRIGGERED (GUI)")

                self.log("🚨 PANIC TRIGGERED!", "error")
                QMessageBox.critical(self, "PANIC", "🚨 PANIC triggered!")
                
        except Exception as e:
            self.log(f"❌ Panic error: {e}", "error")

    def clear_failsafe(self):
        """Clear failsafe"""
        try:
            if not self.connection_established:
                self.log("❌ Not connected", "error")
                return

            self.serial_manager.sendCMD("failsafe", "clear")
            self.event_logger.log_event("CMD: failsafe_clear")
            if self.data_logger is not None:
                self.data_logger.log_event("FAILSAFE_CLEAR_REQUESTED")
            self._apply_failsafe_state(False, "manual_clear", log_event=True)
            self.serial_manager.failsafe_triggered_flag = False
            self.log_emergency_event("Failsafe clear requested from GUI")
            self.log("🔧 Failsafe clear requested", "command")
            
        except Exception as e:
            self.log(f"❌ Failsafe clear error: {e}", "error")

    # ====== GRAPH METHODS ======

    def test_basic_plot(self):
        """Test basic plotting"""
        try:
            self.log("🧪 Testing basic plot...", "info")
            
            if not hasattr(self, 'graph_widget'):
                self.log("❌ No graph widget", "error")
                return
            
            # Clear and create test data
            self.graph_widget.clear_graphs()
            
            x_data = list(range(10))
            y_plate = [20 + i * 2 for i in x_data]
            y_rectal = [37 - i * 0.5 for i in x_data]
            y_target = [25] * len(x_data)
            y_rectal_setpoint = [32 if i > 4 else float('nan') for i in x_data]
            y_adjusted_target = [target + (2 if i > 4 else 0) for i, target in enumerate(y_target)]
            y_pid = [10 * (i % 3) for i in x_data]
            y_breath = [150 - i * 5 for i in x_data]

            test_data = {
                "time": x_data,
                "plate_temp": y_plate,
                "rectal_temp": y_rectal,
                "target_temp": y_target,
                "rectal_target_temp": y_rectal_setpoint,
                "adjusted_target_temp": y_adjusted_target,
                "pid_output": y_pid,
                "breath_rate": y_breath
            }
            
            success = self.graph_widget.update_graphs(test_data)
            
            if success:
                self.log("✅ Test plot successful", "success")
            else:
                self.log("❌ Test plot failed", "error")
                
        except Exception as e:
            self.log(f"❌ Test plot error: {e}", "error")

    def generate_test_data(self):
        """Generate comprehensive test data"""
        try:
            self.log("🎲 Generating test data...", "info")
            
            if not hasattr(self, 'graph_widget'):
                self.log("❌ No graph widget", "error")
                return
            
            # Generate data
            test_data = self.graph_widget.generate_test_data()
            
            if test_data and test_data.get("time"):
                self.graph_data = test_data.copy()
                
                success = self.graph_widget.update_graphs(self.graph_data)
                
                if success:
                    # Update displays
                    self.plateTempDisplay.setText(f"{test_data['plate_temp'][-1]:.2f}°C")
                    self.rectalTempDisplay.setText(f"{test_data['rectal_temp'][-1]:.2f}°C")
                    self.targetTempDisplay.setText(f"{test_data['target_temp'][-1]:.2f}°C")
                    if test_data.get("rectal_target_temp"):
                        self.rectalSetpointDisplay.setText(
                            f"{test_data['rectal_target_temp'][-1]:.2f}°C"
                        )
                    if test_data.get("adjusted_target_temp"):
                        self.adjustedTargetDisplay.setText(
                            f"{test_data['adjusted_target_temp'][-1]:.2f}°C"
                        )
                    self.pidOutputDisplay.setText(f"{test_data['pid_output'][-1]:.1f}")
                    self.breathRateDisplay.setText(f"{test_data['breath_rate'][-1]:.0f} BPM")
                    
                    self.log("✅ Test data generated", "success")
                else:
                    self.log("❌ Test data failed", "error")
            else:
                self.log("❌ Test data empty", "error")
                
        except Exception as e:
            self.log(f"❌ Test data error: {e}", "error")

    def clear_graphs(self):
        """Clear graphs"""
        try:
            if hasattr(self, 'graph_widget'):
                self.graph_widget.clear_graphs()
            
            self.graph_data = {
                "time": [],
                "plate_temp": [],
                "rectal_temp": [],
                "pid_output": [],
                "breath_rate": [],
                "target_temp": [],
                "rectal_target_temp": [],
                "adjusted_target_temp": [],
            }

            self.start_time = None
            self.graph_update_count = 0
            self._reset_profile_timing()

            self.log("🧹 Graphs cleared", "info")
            
        except Exception as e:
            self.log(f"❌ Clear error: {e}", "error")

    # ====== PROFILE METHODS ======

    def _reset_profile_timing(self) -> None:
        """Clear profile runtime tracking so rectal setpoint resets."""

        self.profile_run_start_time = None
        self.profile_pause_time = None
        self.profile_elapsed_paused = 0.0

    def _mark_profile_started(self) -> None:
        """Record that a profile run just started."""

        self.profile_run_start_time = time.time()
        self.profile_pause_time = None
        self.profile_elapsed_paused = 0.0

    def _mark_profile_paused(self) -> None:
        """Record when a running profile is paused."""

        if self.profile_run_start_time is not None and self.profile_pause_time is None:
            self.profile_pause_time = time.time()

    def _mark_profile_resumed(self) -> None:
        """Record when a paused profile resumes."""

        if self.profile_pause_time is not None:
            self.profile_elapsed_paused += max(0.0, time.time() - self.profile_pause_time)
            self.profile_pause_time = None

    def _mark_profile_stopped(self) -> None:
        """Reset timers when a profile run ends."""

        self._reset_profile_timing()

    def _get_profile_elapsed_time(self) -> Optional[float]:
        """Return runtime of active profile excluding paused duration."""

        if self.profile_run_start_time is None:
            return None

        now = time.time()
        elapsed = now - self.profile_run_start_time - self.profile_elapsed_paused
        if self.profile_pause_time is not None:
            elapsed -= max(0.0, now - self.profile_pause_time)

        return max(0.0, elapsed)

    def _build_rectal_setpoint_schedule(
        self, steps: List[Dict[str, Any]]
    ) -> List[Tuple[float, float, float]]:
        """Produce timeline of rectal override targets from controller steps."""

        schedule: List[Tuple[float, float, float]] = []
        cumulative = 0.0

        for step in steps:
            try:
                duration = float(step["total_step_time_ms"]) / 1000.0
            except (KeyError, TypeError, ValueError):
                duration = 0.0

            raw_target = step.get("rectal_override_target", -1000.0)
            try:
                rectal_target = float(raw_target)
            except (TypeError, ValueError):
                rectal_target = -1000.0

            if rectal_target > -999.0 and duration > 0:
                schedule.append((cumulative, cumulative + duration, rectal_target))

            cumulative += max(duration, 0.0)

        return schedule

    def _build_profile_preview_series(
        self, profile_points: List[Dict[str, Any]]
    ) -> Tuple[List[float], List[float], List[float], List[float], List[float]]:
        """Normalize profile points for plotting."""

        times: List[float] = []
        targets: List[float] = []
        plate_targets: List[float] = []
        rectal_times: List[float] = []
        rectal_values: List[float] = []

        for point in profile_points:
            if not isinstance(point, dict):
                continue

            try:
                raw_time = _first_present(point, ("time_min", "time", "t"))
                if raw_time is None:
                    raw_time = len(times)
                time_seconds = float(raw_time) * (60.0 if "time_min" in point or "ramp_min" in point else 1.0)
                times.append(time_seconds)

                target_value = _first_present(
                    point,
                    ("temp", "temp_c", "targetTemp", "target", "plate_target", "plate_end_temp"),
                )
                if target_value is None and targets:
                    target_value = targets[-1]
                targets.append(float(target_value if target_value is not None else 0.0))

                plate_value = _first_present(
                    point,
                    ("plate_target", "plate_end_temp", "actualPlateTarget"),
                )
                if plate_value is None:
                    plate_value = targets[-1]
                plate_targets.append(float(plate_value))

                rectal_value = _first_present(
                    point,
                    (
                        "rectalSetpoint",
                        "rectal_setpoint",
                        "rectalTarget",
                        "rectal_override_target",
                    ),
                )
                if rectal_value is not None:
                    rectal_times.append(time_seconds)
                    rectal_values.append(float(rectal_value))
            except (TypeError, ValueError):
                continue

        if not rectal_values and getattr(self, "rectal_setpoint_schedule", None):
            for start, end, value in self.rectal_setpoint_schedule:
                rectal_times.extend([start, end])
                rectal_values.extend([value, value])

        return times, targets, plate_targets, rectal_times, rectal_values

    def _build_preview_from_steps(
        self, steps: List[Dict[str, Any]]
    ) -> Tuple[List[float], List[float], List[float]]:
        """Fallback builder that uses controller steps when raw points are unavailable."""

        times: List[float] = []
        targets: List[float] = []
        plates: List[float] = []

        for entry in steps:
            try:
                times.append(float(entry.get("t", len(times))))
                target_val = float(entry.get("temp", entry.get("plate_target", 0.0)))
                targets.append(target_val)
                plates.append(target_val)
            except (TypeError, ValueError):
                continue

        return times, targets, plates

    def _update_profile_preview(self) -> None:
        """Refresh inline profile preview plot."""

        if not hasattr(self, "profilePreviewPlot"):
            return

        plot = self.profilePreviewPlot
        if not hasattr(self, "_profile_preview_items"):
            legend = plot.plotItem.legend
            if legend is None:
                legend = plot.addLegend()

            self._profile_preview_items = {
                "target": plot.plot(name="Target", pen=pg.mkPen(color="#0d6efd", width=2)),
                "plate": plot.plot(
                    name="Plate target",
                    pen=pg.mkPen(color="#20c997", width=2, style=Qt.DashLine),
                ),
                "rectal": plot.plot(
                    name="Rectal setpoint",
                    pen=pg.mkPen(color="#343a40", width=2, style=Qt.DotLine),
                ),
            }
            legend.updateSize()

        times: List[float]
        targets: List[float]
        plate_targets: List[float]
        rectal_times: List[float]
        rectal_values: List[float]

        if self.profile_data:
            times, targets, plate_targets, rectal_times, rectal_values = self._build_profile_preview_series(
                self.profile_data
            )
        else:
            times = targets = plate_targets = rectal_times = rectal_values = []

        if not times and getattr(self, "profile_steps", None):
            times, targets, plate_targets = self._build_preview_from_steps(self.profile_steps)
            rectal_times = []
            rectal_values = []
            if getattr(self, "rectal_setpoint_schedule", None):
                for start, end, value in self.rectal_setpoint_schedule:
                    rectal_times.extend([start, end])
                    rectal_values.extend([value, value])

        if not times and not rectal_times:
            for item in self._profile_preview_items.values():
                item.setData([], [])
            plot.enableAutoRange(x=True, y=True)
            return

        self._profile_preview_items["target"].setData(times, targets)
        self._profile_preview_items["plate"].setData(times, plate_targets)
        self._profile_preview_items["rectal"].setData(rectal_times, rectal_values)

        # Fit the entire profile once so the view stays stable instead of auto-playing.
        x_samples = [value for value in list(times) + list(rectal_times) if math.isfinite(value)]
        y_samples = [
            value
            for value in list(targets) + list(plate_targets) + list(rectal_values)
            if math.isfinite(value)
        ]
        if not x_samples or not y_samples:
            plot.enableAutoRange(x=True, y=True)
            return

        x_min, x_max = min(x_samples), max(x_samples)
        y_min, y_max = min(y_samples), max(y_samples)
        y_margin = max((y_max - y_min) * 0.1, 1.0)

        plot.enableAutoRange(x=False, y=False)
        plot.setRange(
            xRange=(x_min, x_max if x_max > x_min else x_min + 60),
            yRange=(y_min - y_margin, y_max + y_margin),
            padding=0,
        )

    def _get_current_rectal_setpoint(self) -> Optional[float]:
        """Return the active rectal setpoint if a profile is running."""

        if not self.rectal_setpoint_schedule:
            return None

        elapsed = self._get_profile_elapsed_time()
        if elapsed is None:
            return None

        for start, end, value in self.rectal_setpoint_schedule:
            if start <= elapsed <= end:
                return value

        return None

    def _extract_rectal_setpoint(self, data: Dict[str, Any]) -> Optional[float]:
        """Prefer firmware-reported rectal setpoints, then fall back to profile schedule."""

        for key in (
            "rectal_override_target",
            "rectal_setpoint",
            "rectal_target_active",
            "rectal_setpoint_active",
        ):
            if key in data:
                try:
                    value = float(data[key])
                    if not math.isnan(value):
                        return value
                except (TypeError, ValueError):
                    continue

        schedule_value = self._get_current_rectal_setpoint()
        return schedule_value

    def _extract_adjusted_plate_target(
        self, data: Dict[str, Any], base_target: Optional[float], rectal_setpoint: Optional[float]
    ) -> Optional[float]:
        """Return a rectal-adjusted plate target when available."""

        for key in (
            "plate_target_rectal",
            "plate_target_modified",
            "rectal_adjusted_plate_target",
            "rectal_plate_target",
        ):
            if key in data:
                try:
                    candidate = float(data[key])
                    if not math.isnan(candidate):
                        return candidate
                except (TypeError, ValueError):
                    continue

        if rectal_setpoint is not None:
            try:
                rectal_temp = float(data.get("anal_probe_temp", float("nan")))
            except (TypeError, ValueError):
                rectal_temp = float("nan")

            if not math.isnan(rectal_temp) and rectal_temp < rectal_setpoint - 0.05:
                fallback = rectal_setpoint
                if base_target is not None and not math.isnan(base_target):
                    fallback = max(base_target, rectal_setpoint)
                return fallback

        return None

    def _refresh_rectal_setpoint_series(self) -> None:
        """Ensure plotted rectal setpoint matches current schedule."""

        count = len(self.graph_data.get("time", []))
        self.graph_data["rectal_target_temp"] = [float("nan")] * count
        if hasattr(self, "graph_widget"):
            self.graph_widget.update_graphs(self.graph_data)

    def _convert_profile_points_to_steps(self, profile_points: List[Dict[str, Any]]):
        """Normalize loader output into controller-ready profile timeline."""

        if not profile_points:
            raise ValueError("Loaded profile is empty")

        def _extract_rectal_target(entry: Dict[str, Any]) -> Optional[float]:
            target = _first_present(
                entry,
                (
                    "rectal_override_target",
                    "rectal_setpoint",
                    "rectalSetpoint",
                    "rectalTarget",
                    "rectal_target",
                ),
            )
            if target is None:
                return None
            try:
                return float(target)
            except (TypeError, ValueError):
                return None

        def _validate_and_append(steps: List[Dict[str, Any]], t_value: float, target: float, index: int):
            if t_value < 0:
                raise ValueError(f"Time cannot be negative at position {index}")

            if steps and t_value <= steps[-1]["t"]:
                raise ValueError(
                    f"Time must be ascending. Entry {index} has t={t_value} which is not greater than previous t={steps[-1]['t']}"
                )

            step_entry: Dict[str, Any] = {"t": t_value, "temp": target}
            rectal_value = _extract_rectal_target(profile_points[index - 1])
            if rectal_value is not None:
                step_entry["rectal_override_target"] = rectal_value

            steps.append(step_entry)

        # Case 1: Already in controller timeline format
        first_entry = profile_points[0]
        if "t" in first_entry and ("temp" in first_entry or "plate_target" in first_entry):
            steps: List[Dict[str, Any]] = []
            for idx, entry in enumerate(profile_points, start=1):
                try:
                    t_value = float(entry["t"])
                    target = float(entry.get("temp", entry.get("plate_target")))
                except (TypeError, ValueError, KeyError) as exc:
                    raise ValueError(f"Invalid timeline entry at position {idx}: {exc}") from exc

                _validate_and_append(steps, t_value, target, idx)

            if len(steps) > 10:
                raise ValueError("Profile may contain at most 10 steps")

            return steps

        step_keys = {"plate_start_temp", "plate_end_temp", "total_step_time_ms"}
        if step_keys.issubset(first_entry.keys()):
            steps: List[Dict[str, Any]] = []
            cumulative_sec = 0.0

            for index, entry in enumerate(profile_points, start=1):
                try:
                    start_temp = float(entry["plate_start_temp"])
                    end_temp = float(entry["plate_end_temp"])
                    total_time_ms = int(float(entry["total_step_time_ms"]))
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid step entry at position {index}: {exc}"
                    ) from exc

                if total_time_ms <= 0:
                    raise ValueError(
                        f"total_step_time_ms must be positive at step {index}"
                    )

                if not steps:
                    _validate_and_append(steps, 0.0, start_temp, index)

                cumulative_sec += total_time_ms / 1000.0
                _validate_and_append(steps, cumulative_sec, end_temp, index)

            if len(steps) > 10:
                raise ValueError("Profile may contain at most 10 steps")

            return steps

        try:
            ordered_points = sorted(
                profile_points,
                key=lambda entry: float(entry["time_min"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Profile entries must include valid 'time_min' values") from exc

        steps: List[Dict[str, Any]] = []

        for index, entry in enumerate(ordered_points, start=1):
            try:
                target_temp = float(entry.get("plate_target", entry["temp_c"]))
                t_value = float(entry["time_min"]) * 60.0
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid profile entry at position {index}") from exc

            _validate_and_append(steps, t_value, target_temp, index)

        if len(steps) > 10:
            raise ValueError("Profile may contain at most 10 steps")

        return steps

    def _update_profile_button_states(self):
        """Enable or disable profile controls based on current state."""

        if not hasattr(self, "startProfileButton"):
            return

        connected = self.connection_established
        uploading = self.profile_upload_pending
        active = self.profile_active
        paused = self.profile_paused and active
        ready = self.profile_ready and connected and not uploading and not active

        self.startProfileButton.setEnabled(ready)
        self.pauseProfileButton.setEnabled(connected and active and not paused)
        self.resumeProfileButton.setEnabled(connected and paused)
        self.stopProfileButton.setEnabled(connected and (active or paused))

    def load_profile(self):
        """Load temperature profile and upload it to the controller."""

        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Load Profile",
                "",
                "JSON Files (*.json);;CSV Files (*.csv)"
            )

            if not file_name:
                return

            success = False
            if file_name.endswith('.json'):
                success = self.profile_loader.load_profile_json(file_name)
            elif file_name.endswith('.csv'):
                success = self.profile_loader.load_profile_csv(file_name)

            if not success:
                self.log("❌ Profile load failed", "error")
                QMessageBox.warning(self, "Load Error", "Failed to load the selected profile file.")
                return

            self.profile_data = self.profile_loader.get_profile()
            filename = os.path.basename(file_name)
            self.profileFileLabel.setText(f"✅ {filename}")
            self.profileFileLabel.setStyleSheet("color: #28a745; font-weight: bold;")

            try:
                self.profile_steps = self._convert_profile_points_to_steps(self.profile_data)
                self.rectal_setpoint_schedule = self._build_rectal_setpoint_schedule(
                    self.profile_steps
                )
                self._refresh_rectal_setpoint_series()
                self._update_profile_preview()
            except ValueError as exc:
                self.profile_steps = []
                self.rectal_setpoint_schedule = []
                self._refresh_rectal_setpoint_series()
                self._update_profile_preview()
                self.profile_ready = False
                self.profile_upload_pending = False
                self.profile_active = False
                self.profile_paused = False
                self._reset_profile_timing()
                self._update_profile_button_states()
                error_message = f"Profile conversion error: {exc}"
                self.log(f"❌ {error_message}", "error")
                QMessageBox.warning(self, "Profile Error", error_message)
                return

            if not self.profile_steps:
                self.rectal_setpoint_schedule = []
                self._refresh_rectal_setpoint_series()
                self._update_profile_preview()
                self.profile_ready = False
                self.profile_upload_pending = False
                self.profile_active = False
                self.profile_paused = False
                self._update_profile_button_states()
                self.log("❌ Profile did not produce any steps", "error")
                QMessageBox.warning(
                    self,
                    "Profile Error",
                    "The loaded profile did not produce any controller steps."
                )
                return

            self.profile_ready = False
            self.profile_upload_pending = False
            self.profile_active = False
            self.profile_paused = False
            self._reset_profile_timing()
            self._update_profile_button_states()

            self.log(f"✅ Profile loaded: {filename}", "success")
            self.event_logger.log_event(f"Profile loaded: {file_name}")

            if self.connection_established:
                try:
                    self.serial_manager.sendSET("profile_data", self.profile_steps)
                except Exception as exc:
                    self.log(f"❌ Failed to upload profile: {exc}", "error")
                    QMessageBox.warning(
                        self,
                        "Upload Error",
                        f"Failed to upload the profile to the controller.\n{exc}"
                    )
                    return

                self.profile_upload_pending = True
                self._update_profile_button_states()
                self.log(
                    f"📤 Uploading {len(self.profile_steps)} profile steps to controller...",
                    "info",
                )
                self.event_logger.log_event(
                    f"Profile upload requested: {len(self.profile_steps)} steps"
                )
            else:
                self.log(
                    "⚠️ Connect to the controller to upload the loaded profile.",
                    "warning",
                )

        except Exception as e:
            self.log(f"❌ Profile error: {e}", "error")

    # ====== CONNECTION METHODS ======

    def refresh_ports(self):
        """Refresh ports"""
        try:
            self.portSelector.clear()
            ports = self.serial_manager.list_ports()
            self.portSelector.addItems(ports)
            self.log(f"🔄 Found {len(ports)} ports", "info")
            
        except Exception as e:
            self.log(f"❌ Port refresh error: {e}", "error")

    def toggle_connection(self):
        """Toggle connection"""
        try:
            if self.serial_manager.is_connected():
                # Disconnect
                self.serial_manager.disconnect()
                self._stop_data_logger()
                self.connectButton.setText("Connect")
                self.connectionStatusLabel.setText("❌ Disconnected")
                self.connectionStatusLabel.setStyleSheet("color: red; font-weight: bold;")
                self.connection_established = False
                self.start_time = None

                self.profile_ready = False
                self.profile_upload_pending = False
                self.profile_active = False
                self.profile_paused = False
                self._update_profile_button_states()

                self.log("🔌 Disconnected", "info")
                self.event_logger.log_event("Disconnected")

            else:
                # Connect
                port = self.portSelector.currentText()
                if not port:
                    QMessageBox.warning(self, "No Port", "Please select a port")
                    return
                    
                if self.serial_manager.connect(port):
                    self.connectButton.setText("Disconnect")
                    self.connectionStatusLabel.setText(f"✅ Connected to {port}")
                    self.connectionStatusLabel.setStyleSheet("color: green; font-weight: bold;")
                    self.connection_established = True

                    self.log(f"🔌 Connected to {port}", "success")
                    self.event_logger.log_event(f"Connected to {port}")

                    if self.disable_breath_check:
                        try:
                            self.serial_manager.sendSET("breath_check_enabled", False)
                            self.log("⚠️ Breath-stop check sent to controller (disabled)", "warning")
                        except Exception as exc:
                            self.log(f"⚠️ Failed to sync breath-stop check: {exc}", "warning")

                    # Start sync
                    self.sync_timer.start(1000)

                    if self.profile_steps:
                        try:
                            self.serial_manager.sendSET("profile_data", self.profile_steps)
                        except Exception as exc:
                            self.log(f"⚠️ Failed to upload stored profile on connect: {exc}", "warning")
                            self._update_profile_button_states()
                        else:
                            self.profile_ready = False
                            self.profile_upload_pending = True
                            self.profile_active = False
                            self.profile_paused = False
                            self._update_profile_button_states()
                            self.log(
                                f"📤 Uploading {len(self.profile_steps)} stored profile steps to controller...",
                                "info",
                            )
                            self.event_logger.log_event(
                                f"Profile upload requested: {len(self.profile_steps)} steps"
                            )
                    else:
                        self._update_profile_button_states()

                else:
                    QMessageBox.critical(self, "Connection Failed", f"Failed to connect to {port}")
                    self.log(f"❌ Connection failed: {port}", "error")
                    
        except Exception as e:
            self.log(f"❌ Connection error: {e}", "error")

    def initial_sync(self):
        """Initial sync after connection"""
        try:
            if self.serial_manager.is_connected():
                self.log("🔄 Syncing...", "info")
                
                self.serial_manager.sendCMD("get", "pid_params")
                QTimer.singleShot(300, lambda: self.serial_manager.sendCMD("get", "status"))
                
        except Exception as e:
            self.log(f"❌ Sync error: {e}", "error")

    def request_status(self):
        """Request status"""
        try:
            if self.serial_manager.is_connected():
                self.serial_manager.sendCMD("get", "status")
        except Exception as e:
            pass  # Silent fail

    # ====== UTILITY METHODS ======

    def log(self, message: str, level: str = "info"):
        """Enhanced logging"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            
            colors = {
                "error": "#dc3545",
                "warning": "#fd7e14",
                "success": "#28a745",
                "command": "#007bff",
                "info": "#212529"
            }

            color = colors.get(level, colors["info"])
            formatted_message = f'<span style="color: {color}; font-weight: bold;">[{timestamp}]</span> {message}'

            scrollbar = self.logBox.verticalScrollBar()
            previous_value = scrollbar.value()
            previous_max = scrollbar.maximum()

            self.logBox.append(formatted_message)

            if self.autoScrollCheckbox.isChecked():
                scrollbar.setValue(scrollbar.maximum())
            else:
                # Preserve the user's scroll position when auto-scroll is off
                if previous_max != scrollbar.maximum():
                    delta = scrollbar.maximum() - previous_max
                    scrollbar.setValue(max(0, previous_value + delta))
                else:
                    scrollbar.setValue(previous_value)
                
            print(f"LOG: {message}")
            
        except Exception as e:
            print(f"LOG ERROR: {e} - Message: {message}")

    def closeEvent(self, event):
        """Handle close event"""
        try:
            self.log("👋 Application closing...", "info")
            
            # Stop timers
            if hasattr(self, 'status_timer'):
                self.status_timer.stop()
            if hasattr(self, 'sync_timer'):
                self.sync_timer.stop()
            
            # Disconnect serial
            if self.serial_manager.is_connected():
                self.serial_manager.disconnect()

            self._stop_data_logger()

            # Close loggers
            try:
                self.event_logger.close()
            except:
                pass
            
            self.log("✅ Cleanup complete", "success")
            
        except Exception as e:
            print(f"Shutdown error: {e}")
        
        event.accept()


def main():
    """Main entry point"""
    try:
        print("🚀 Starting Musehypothermi GUI v3.0 with Asymmetric PID...")
        
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("Musehypothermi GUI")
        app.setApplicationVersion("3.0")
        app.setStyle('Fusion')
        
        print("✅ QApplication created")
        
        # Create and show window
        window = MainWindow()
        window.show()
        
        print("✅ Application started successfully")
        
        # Run application
        return app.exec()
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())