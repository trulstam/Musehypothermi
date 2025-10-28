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
    QDialogButtonBox, QDoubleSpinBox, QStackedWidget
)
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont, QPalette, QColor

# Matplotlib imports
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# Local imports
from serial_comm import SerialManager
from event_logger import EventLogger
from profile_loader import ProfileLoader

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

        cooling_group = QGroupBox("Cooling PID (Conservative)")
        cooling_layout = QGridLayout()
        cooling_layout.setHorizontalSpacing(14)
        cooling_layout.setVerticalSpacing(8)

        self.kp_cooling_input = QLineEdit("0.8")
        self.kp_cooling_input.setMinimumWidth(120)
        self.ki_cooling_input = QLineEdit("0.02")
        self.ki_cooling_input.setMinimumWidth(120)
        self.kd_cooling_input = QLineEdit("3.0")
        self.kd_cooling_input.setMinimumWidth(120)

        cooling_layout.addWidget(QLabel("Kp"), 0, 0)
        cooling_layout.addWidget(self.kp_cooling_input, 0, 1)
        cooling_layout.addWidget(QLabel("0.1 – 2.0"), 0, 2)

        cooling_layout.addWidget(QLabel("Ki"), 1, 0)
        cooling_layout.addWidget(self.ki_cooling_input, 1, 1)
        cooling_layout.addWidget(QLabel("0.01 – 0.10"), 1, 2)

        cooling_layout.addWidget(QLabel("Kd"), 2, 0)
        cooling_layout.addWidget(self.kd_cooling_input, 2, 1)
        cooling_layout.addWidget(QLabel("0.5 – 5.0"), 2, 2)

        self.set_cooling_pid_button = QPushButton("Apply Cooling PID")
        self.set_cooling_pid_button.clicked.connect(self.set_cooling_pid)
        cooling_layout.addWidget(self.set_cooling_pid_button, 3, 0, 1, 3)
        cooling_layout.setColumnStretch(1, 1)

        cooling_group.setLayout(cooling_layout)

        heating_group = QGroupBox("Heating PID (Aggressive)")
        heating_layout = QGridLayout()
        heating_layout.setHorizontalSpacing(14)
        heating_layout.setVerticalSpacing(8)

        self.kp_heating_input = QLineEdit("2.5")
        self.kp_heating_input.setMinimumWidth(120)
        self.ki_heating_input = QLineEdit("0.2")
        self.ki_heating_input.setMinimumWidth(120)
        self.kd_heating_input = QLineEdit("1.2")
        self.kd_heating_input.setMinimumWidth(120)

        heating_layout.addWidget(QLabel("Kp"), 0, 0)
        heating_layout.addWidget(self.kp_heating_input, 0, 1)
        heating_layout.addWidget(QLabel("0.5 – 5.0"), 0, 2)

        heating_layout.addWidget(QLabel("Ki"), 1, 0)
        heating_layout.addWidget(self.ki_heating_input, 1, 1)
        heating_layout.addWidget(QLabel("0.05 – 1.0"), 1, 2)

        heating_layout.addWidget(QLabel("Kd"), 2, 0)
        heating_layout.addWidget(self.kd_heating_input, 2, 1)
        heating_layout.addWidget(QLabel("0.1 – 3.0"), 2, 2)

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
                if data["emergency_stop"]:
                    self._update_label_styles(
                        [self.emergency_status_label, self.external_emergency_label],
                        "🚨 ACTIVE",
                        "color: #dc3545; font-weight: bold;",
                    )
                else:
                    self._update_label_styles(
                        [self.emergency_status_label, self.external_emergency_label],
                        "✅ Clear",
                        "color: #28a745; font-weight: bold;",
                    )
            
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
        """Set cooling PID parameters with validation"""
        try:
            kp = float(self.kp_cooling_input.text())
            ki = float(self.ki_cooling_input.text())
            kd = float(self.kd_cooling_input.text())
            
            # Validate cooling parameters (conservative limits)
            if not (0.1 <= kp <= 2.0):
                raise ValueError("Cooling Kp must be 0.1-2.0 (conservative)")
            if not (0.01 <= ki <= 0.1):
                raise ValueError("Cooling Ki must be 0.01-0.1 (prevent windup)")
            if not (0.5 <= kd <= 5.0):
                raise ValueError("Cooling Kd must be 0.5-5.0 (damping)")
            
            if self.parent.send_asymmetric_command("set_cooling_pid", {"kp": kp, "ki": ki, "kd": kd}):
                self.parent.log(f"❄️ Cooling PID set: Kp={kp:.3f}, Ki={ki:.4f}, Kd={kd:.3f}", "success")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Cooling PID error: {e}")
            self.parent.log(f"❌ Invalid cooling PID: {e}", "error")
    
    def set_heating_pid(self):
        """Set heating PID parameters with validation"""
        try:
            kp = float(self.kp_heating_input.text())
            ki = float(self.ki_heating_input.text())
            kd = float(self.kd_heating_input.text())

            # Validate heating parameters (more aggressive allowed)
            if not (0.5 <= kp <= 5.0):
                raise ValueError("Heating Kp must be 0.5-5.0")
            if not (0.05 <= ki <= 1.0):
                raise ValueError("Heating Ki must be 0.05-1.0")
            if not (0.1 <= kd <= 3.0):
                raise ValueError("Heating Kd must be 0.1-3.0")

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

            if not (0.1 <= cool_kp <= 2.0):
                raise ValueError("Cooling Kp must be 0.1-2.0")
            if not (0.01 <= cool_ki <= 0.1):
                raise ValueError("Cooling Ki must be 0.01-0.1")
            if not (0.5 <= cool_kd <= 5.0):
                raise ValueError("Cooling Kd must be 0.5-5.0")

            # Heating values
            heat_kp = float(self.kp_heating_input.text())
            heat_ki = float(self.ki_heating_input.text())
            heat_kd = float(self.kd_heating_input.text())

            if not (0.5 <= heat_kp <= 5.0):
                raise ValueError("Heating Kp must be 0.5-5.0")
            if not (0.05 <= heat_ki <= 1.0):
                raise ValueError("Heating Ki must be 0.05-1.0")
            if not (0.1 <= heat_kd <= 3.0):
                raise ValueError("Heating Kd must be 0.1-3.0")

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

        kp = 0.0
        ki = 0.0
        kd = 0.0
        if process_gain != 0 and dead_time > 0:
            kp = 1.2 * time_constant / (process_gain * dead_time)
            ki = kp / (2.0 * dead_time)
            kd = kp * dead_time * 0.5

        kp = float(np.clip(kp, 0.01, 20.0))
        ki = float(np.clip(ki, 0.001, 5.0))
        kd = float(np.clip(kd, 0.0, 10.0))

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
        }


class AutotuneWizardTab(QWidget):
    """Guided autotune workflow with live analysis and UI."""

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
            "• Wizzarden setter automatisk et temperatursprang og følger reaksjonen.\n"
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
        config_layout.addRow("Stegstørrelse:", self.step_spin)

        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Varme (øke mål)", "heating")
        self.direction_combo.addItem("Kjøling (senke mål)", "cooling")
        config_layout.addRow("Retning:", self.direction_combo)

        config_group.setLayout(config_layout)
        vbox.addWidget(config_group)

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
        self.kp_spin.setRange(0.0, 20.0)
        self.kp_spin.setDecimals(3)
        self.kp_spin.setSingleStep(0.05)

        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(0.0, 5.0)
        self.ki_spin.setDecimals(4)
        self.ki_spin.setSingleStep(0.01)

        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(0.0, 10.0)
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

        buttons = QHBoxLayout()
        self.apply_button = QPushButton("Aktiver varme-PID")
        self.apply_button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.apply_button.clicked.connect(self.apply_to_heating)

        self.apply_both_button = QPushButton("Aktiver begge")
        self.apply_both_button.setStyleSheet("background-color: #6f42c1; color: white; font-weight: bold;")
        self.apply_both_button.clicked.connect(self.apply_to_both)

        self.restart_button = QPushButton("Kjør på nytt")
        self.restart_button.clicked.connect(self.reset_wizard)

        buttons.addStretch()
        buttons.addWidget(self.apply_button)
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
        self.collect_status.setText("Setter steg...")
        self.collect_status.setStyleSheet("color: #17a2b8; font-weight: bold;")
        self.metric_label.setText("ΔT: –  |  Hastighet: –  |  Overshoot: –")
        self.finish_button.setEnabled(False)
        self.stack.setCurrentIndex(1)
        self._autotune_command_sent = False

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
        direction = self.direction_combo.currentData()
        step = self.step_spin.value()

        target_min = -10.0
        target_max = 50.0

        if direction == "heating":
            base = max(target_temp, plate_temp)
            new_target = min(target_max, base + step)
        else:
            base = min(target_temp, plate_temp)
            new_target = max(target_min, base - step)

        if abs(new_target - base) < 1e-6:
            QMessageBox.warning(
                self,
                "Ugyldig steg",
                "Valgt steg kunne ikke beregnes innenfor temperaturområdet. Juster størrelsen eller retningen.",
            )
            self.collecting = False
            self.stack.setCurrentIndex(0)
            return

        if not self.parent.pid_running:
            self.parent.send_and_log_cmd("pid", "start")

        if not self.parent.send_target_temperature(
            new_target,
            source="autotune steg",
            silent=True,
        ):
            QMessageBox.warning(self, "Kunne ikke sette mål", "Måltemperaturen kunne ikke oppdateres.")
            self.collecting = False
            self.stack.setCurrentIndex(0)
            return

        self.collect_status.setText(
            f"Steg aktivt: mål {new_target:.1f} °C (fra {self._original_target:.1f} °C)"
        )
        self.parent.log(
            f"🎯 Autotune steg start: {self._original_target:.1f} → {new_target:.1f} °C ({'oppvarming' if direction == 'heating' else 'nedkjøling'})",
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
        self._restore_original_target()
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
        self._restore_original_target()

    def apply_to_heating(self) -> None:
        kp = self.kp_spin.value()
        ki = self.ki_spin.value()
        kd = self.kd_spin.value()
        self.parent.asymmetric_controls.kp_heating_input.setText(f"{kp:.3f}")
        self.parent.asymmetric_controls.ki_heating_input.setText(f"{ki:.4f}")
        self.parent.asymmetric_controls.kd_heating_input.setText(f"{kd:.3f}")
        self.parent.asymmetric_controls.set_heating_pid()

    def apply_to_both(self) -> None:
        kp = self.kp_spin.value()
        ki = self.ki_spin.value()
        kd = self.kd_spin.value()
        self.parent.asymmetric_controls.kp_heating_input.setText(f"{kp:.3f}")
        self.parent.asymmetric_controls.ki_heating_input.setText(f"{ki:.4f}")
        self.parent.asymmetric_controls.kd_heating_input.setText(f"{kd:.3f}")
        self.parent.asymmetric_controls.set_heating_pid()

        self.parent.asymmetric_controls.kp_cooling_input.setText(f"{(kp * 0.5):.3f}")
        self.parent.asymmetric_controls.ki_cooling_input.setText(f"{(ki * 0.5):.4f}")
        self.parent.asymmetric_controls.kd_cooling_input.setText(f"{(kd * 0.5):.3f}")
        self.parent.asymmetric_controls.set_cooling_pid()

    def receive_data(self, data: Dict[str, Any]) -> None:
        if self._autotune_command_sent:
            status_raw = str(data.get("autotune_status", "")).strip()
            if status_raw:
                status_readable = status_raw.replace("_", " ").title()
                self.collect_status.setText(f"Firmware-autotune: {status_readable}")
                lower = status_readable.lower()
                if lower.startswith("abort") or lower in {"aborted", "idle"}:
                    self.metric_label.setText("Autotune avbrutt av kontrolleren.")
                    self._autotune_command_sent = False
                elif lower in {"done", "complete", "finished"}:
                    self.metric_label.setText("Resultater mottatt fra kontrolleren.")
                    self._autotune_command_sent = False
            return

        if not self.collecting:
            return
        if "cooling_plate_temp" not in data or "pid_output" not in data:
            return

        timestamp = time.time()
        temp = float(data["cooling_plate_temp"])
        output = float(data.get("pid_output", 0.0))
        self.analyzer.add_sample(timestamp, temp, output)

        now = time.time()
        if now - self._last_plot_update > 0.5:
            self._last_plot_update = now
            self._update_collect_plot()

        if self.analyzer.has_enough_samples():
            metrics = self.analyzer.compute_results()
            if metrics:
                self.metric_label.setText(
                    f"ΔT: {metrics['delta_temp']:.2f} °C  |  Hastighet: {metrics['max_rate']:.3f} °C/s  |  Overshoot: {metrics['overshoot']:.2f} °C"
                )
                self.finish_button.setEnabled(True)

                if self.analyzer.is_stable():
                    self.collect_status.setText("Stabilt - analyserer...")
                    self.collect_status.setStyleSheet("color: #28a745; font-weight: bold;")
                    self.collecting = False
                    self._present_results(metrics)
            else:
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

    def _present_results(self, results: Dict[str, float]) -> None:
        self.stack.setCurrentIndex(2)

        summary = (
            f"ΔT: {results['delta_temp']:.2f} °C\n"
            f"Hastighet: {results['max_rate']:.3f} °C/s\n"
            f"Overshoot: {results['overshoot']:.2f} °C\n"
            f"Settlingstid: {results['settling_time']:.1f} s\n"
            f"Prosessgain: {results['process_gain']:.2f}\n"
            f"Dødtid L: {results['dead_time']:.2f} s  |  Tidskonstant T: {results['time_constant']:.2f} s"
        )
        self.results_summary.setText(summary)

        self.kp_spin.setValue(results['kp'])
        self.ki_spin.setValue(results['ki'])
        self.kd_spin.setValue(results['kd'])

        if self._result_axes is not None and self._result_canvas is not None:
            self._result_axes.clear()
            self._result_axes.set_title("Temperaturrespons")
            self._result_axes.set_xlabel("Tid [s]")
            self._result_axes.set_ylabel("Temp [°C]")
            self._result_axes.grid(True, alpha=0.3)
            self._result_axes.plot(
                self.analyzer.timestamps,
                self.analyzer.temperatures,
                color="#ff6b35",
                label="Plate temp",
            )
            self._result_axes.legend()
            self._result_canvas.draw()

        self._autotune_command_sent = False
        self._restore_original_target()

    def display_results(self, results: Dict[str, float]) -> None:
        """Expose results rendering to the parent GUI."""
        self.collecting = False
        self._present_results(results)

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
                f"🎯 Autotune: måltemperatur tilbake til {self._original_target:.1f} °C",
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
        self.setup_plots()
        self.setup_layout()
        self.max_points = 200
        self.update_counter = 0
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
            
            # PID subplot
            self.ax_pid = self.figure.add_subplot(gs[1])
            self.ax_pid.set_title('PID Output', fontsize=12, fontweight='bold')
            self.ax_pid.set_ylabel('PID Output', fontsize=11)
            self.ax_pid.grid(True, alpha=0.3)
            self.ax_pid.set_facecolor('#f0f8ff')
            
            # Breath subplot
            self.ax_breath = self.figure.add_subplot(gs[2])
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
            
            print("✅ Matplotlib plots configured")
            
        except Exception as e:
            print(f"❌ Plot setup error: {e}")
            raise

    def setup_layout(self):
        """Setup widget layout"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
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
                all_temps = graph_data["plate_temp"] + graph_data["rectal_temp"] + graph_data["target_temp"]
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

            return {
                "time": times,
                "plate_temp": plate_temps,
                "rectal_temp": rectal_temps,
                "target_temp": target_temps,
                "rectal_target_temp": rectal_targets,
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
                "pid_output": [],
                "breath_rate": [],
            }


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
        }

        self.connection_established = False
        self.start_time = None
        self.max_graph_points = 200
        self.data_update_count = 0
        self.graph_update_count = 0
        self.last_heating_limit = 35.0
        self.last_cooling_limit = 35.0
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
        status_row.addWidget(self.failsafeIndicator)
        
        self.pidStatusIndicator = QLabel("⚫ PID Off")
        self.pidStatusIndicator.setStyleSheet("color: gray; font-weight: bold;")
        status_row.addWidget(self.pidStatusIndicator)
        
        status_row.addStretch()
        
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
        data_layout.addWidget(QLabel("⚡ PID Output:"), 3, 0)
        data_layout.addWidget(self.pidOutputDisplay, 3, 1)
        data_layout.addWidget(QLabel("🫁 Breath Rate:"), 4, 0)
        data_layout.addWidget(self.breathRateDisplay, 4, 1)
        
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

        advanced_layout.addWidget(self.refreshPidButton, 0, 0)
        advanced_layout.addWidget(self.applyBothPidButton, 0, 1)
        advanced_layout.addWidget(self.setMaxOutputButton, 1, 0)
        advanced_layout.addWidget(self.saveEEPROMButton, 1, 1)
        advanced_layout.addWidget(self.requestStatusButton, 2, 0)
        advanced_layout.addWidget(self.clearFailsafeButton, 2, 1)

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
        
        controls_layout.addWidget(self.testBasicPlotButton)
        controls_layout.addWidget(self.generateTestDataButton)
        controls_layout.addWidget(self.clearGraphsButton)
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

    def init_managers(self):
        """Initialize managers"""
        try:
            # Serial manager
            self.serial_manager = SerialManager()
            self.serial_manager.on_data_received = self.process_incoming_data
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
            self.status_timer.start(3000)
            
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

    def send_and_log_cmd(self, action: str, state: str) -> bool:
        """Send command with error handling"""
        try:
            if not self.connection_established:
                self.log("❌ Not connected", "error")
                return False
                
            self.serial_manager.sendCMD(action, state)
            self.event_logger.log_event(f"CMD: {action} → {state}")
            self.log(f"📡 Sent: {action} = {state}", "command")
            return True
            
        except Exception as e:
            self.log(f"❌ Command error: {e}", "error")
            return False

    def process_incoming_data(self, data: Dict[str, Any]):
        """Process incoming data from Arduino"""
        if not data:
            return

        try:
            self.data_update_count += 1
            
            # Update live displays
            self.update_live_displays(data)
            
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

    def update_live_displays(self, data: Dict[str, Any]):
        """Update live data displays"""
        try:
            if "cooling_plate_temp" in data:
                temp = float(data["cooling_plate_temp"])
                self.plateTempDisplay.setText(f"{temp:.1f}°C")
                self.current_plate_temp = temp

            if "anal_probe_temp" in data:
                temp = float(data["anal_probe_temp"])
                self.rectalTempDisplay.setText(f"{temp:.1f}°C")

            if "pid_output" in data:
                output = float(data["pid_output"])
                self.pidOutputDisplay.setText(f"{output:.1f}")

            if "plate_target_active" in data:
                target = float(data["plate_target_active"])
                self.targetTempDisplay.setText(f"{target:.1f}°C")
                self.current_target_temp = target

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
            # Failsafe
            if "failsafe_active" in data:
                if data["failsafe_active"]:
                    reason = data.get("failsafe_reason", "Unknown")
                    self.failsafeIndicator.setText(f"🔴 FAILSAFE: {reason}")
                    self.failsafeIndicator.setStyleSheet("color: #dc3545; font-weight: bold;")
                else:
                    self.failsafeIndicator.setText("🟢 Safe")
                    self.failsafeIndicator.setStyleSheet("color: #28a745; font-weight: bold;")

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
                else:
                    self._mark_profile_stopped()
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
            self.graph_data["target_temp"].append(float(data.get("plate_target_active", 37)))

            rectal_setpoint = self._get_current_rectal_setpoint()
            if rectal_setpoint is None:
                self.graph_data["rectal_target_temp"].append(float("nan"))
            else:
                self.graph_data["rectal_target_temp"].append(float(rectal_setpoint))
            
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
            if all(key in results for key in ["kp", "ki", "kd"]):
                kp = float(results["kp"])
                ki = float(results["ki"])
                kd = float(results["kd"])

                if hasattr(self, "asymmetric_controls"):
                    self.asymmetric_controls.kp_heating_input.setText(f"{kp:.3f}")
                    self.asymmetric_controls.ki_heating_input.setText(f"{ki:.3f}")
                    self.asymmetric_controls.kd_heating_input.setText(f"{kd:.3f}")

                if hasattr(self, "autotune_wizard"):
                    self.autotune_wizard.display_results(results)

                QMessageBox.information(
                    self,
                    "🎯 Autotune Complete",
                    f"New heating PID parameters:\n\n"
                    f"Kp: {kp:.3f}\n"
                    f"Ki: {ki:.3f}\n"
                    f"Kd: {kd:.3f}\n\n"
                    f"Review and apply via the heating PID controls."
                )

                self.log(f"🎯 Autotune: Kp={kp:.3f}, Ki={ki:.3f}, Kd={kd:.3f}", "success")
                
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
                self.event_logger.log_event("CMD: panic triggered")
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
                
            self.serial_manager.sendCMD("failsafe_clear", "")
            self.event_logger.log_event("CMD: failsafe_clear")
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
            y_pid = [10 * (i % 3) for i in x_data]
            y_breath = [150 - i * 5 for i in x_data]
            
            test_data = {
                "time": x_data,
                "plate_temp": y_plate,
                "rectal_temp": y_rectal,
                "target_temp": y_target,
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
                    self.plateTempDisplay.setText(f"{test_data['plate_temp'][-1]:.1f}°C")
                    self.rectalTempDisplay.setText(f"{test_data['rectal_temp'][-1]:.1f}°C")
                    self.targetTempDisplay.setText(f"{test_data['target_temp'][-1]:.1f}°C")
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

    def _refresh_rectal_setpoint_series(self) -> None:
        """Ensure plotted rectal setpoint matches current schedule."""

        count = len(self.graph_data.get("time", []))
        self.graph_data["rectal_target_temp"] = [float("nan")] * count
        if hasattr(self, "graph_widget"):
            self.graph_widget.update_graphs(self.graph_data)

    def _convert_profile_points_to_steps(self, profile_points: List[Dict[str, Any]]):
        """Normalize loader output into controller-ready profile steps."""

        if not profile_points:
            raise ValueError("Loaded profile is empty")

        first_entry = profile_points[0]
        step_keys = {"plate_start_temp", "plate_end_temp", "total_step_time_ms"}

        if step_keys.issubset(first_entry.keys()):
            steps: List[Dict[str, Any]] = []

            for index, entry in enumerate(profile_points, start=1):
                try:
                    start_temp = float(entry["plate_start_temp"])
                    end_temp = float(entry["plate_end_temp"])
                    total_time_ms = int(float(entry["total_step_time_ms"]))
                    ramp_time_ms = int(float(entry.get("ramp_time_ms", 0)))
                    rectal_target = entry.get("rectal_override_target", -1000.0)
                    rectal_target = (
                        float(rectal_target)
                        if rectal_target is not None
                        else -1000.0
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid step entry at position {index}: {exc}"
                    ) from exc

                if total_time_ms <= 0:
                    raise ValueError(
                        f"total_step_time_ms must be positive at step {index}"
                    )

                if ramp_time_ms < 0:
                    raise ValueError(
                        f"ramp_time_ms cannot be negative at step {index}"
                    )

                if ramp_time_ms > total_time_ms:
                    raise ValueError(
                        f"ramp_time_ms cannot exceed total_step_time_ms at step {index}"
                    )

                steps.append(
                    {
                        "plate_start_temp": start_temp,
                        "plate_end_temp": end_temp,
                        "ramp_time_ms": ramp_time_ms,
                        "rectal_override_target": rectal_target,
                        "total_step_time_ms": total_time_ms,
                    }
                )

            if len(steps) > 10:
                raise ValueError("Profile may contain at most 10 steps")

            return steps

        if len(profile_points) < 2:
            raise ValueError("Profile must contain at least two time points")

        try:
            ordered_points = sorted(
                profile_points,
                key=lambda entry: float(entry["time_min"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Profile entries must include valid 'time_min' values") from exc

        steps: List[Dict[str, Any]] = []

        for index in range(1, len(ordered_points)):
            previous = ordered_points[index - 1]
            current = ordered_points[index]

            try:
                previous_temp = float(previous["temp_c"])
                current_temp = float(current["temp_c"])
                previous_time = float(previous["time_min"])
                current_time = float(current["time_min"])
                ramp_minutes = float(current.get("ramp_min", 0.0))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid profile entry at position {index + 1}") from exc

            duration_minutes = current_time - previous_time
            if duration_minutes <= 0:
                raise ValueError(
                    f"Profile time at step {index + 1} must be greater than previous step"
                )

            total_step_time_ms = int(duration_minutes * 60000)
            ramp_minutes = max(0.0, min(ramp_minutes, duration_minutes))
            ramp_time_ms = int(ramp_minutes * 60000)

            steps.append({
                "plate_start_temp": previous_temp,
                "plate_end_temp": current_temp,
                "ramp_time_ms": ramp_time_ms,
                "rectal_override_target": -1000.0,
                "total_step_time_ms": total_step_time_ms,
            })

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
            except ValueError as exc:
                self.profile_steps = []
                self.rectal_setpoint_schedule = []
                self._refresh_rectal_setpoint_series()
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
                    self.serial_manager.sendSET("profile", self.profile_steps)
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

                    # Start sync
                    self.sync_timer.start(1000)

                    if self.profile_steps:
                        try:
                            self.serial_manager.sendSET("profile", self.profile_steps)
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
            
            self.logBox.append(formatted_message)
            
            if self.autoScrollCheckbox.isChecked():
                scrollbar = self.logBox.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
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