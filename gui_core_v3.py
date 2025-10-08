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
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel,
    QVBoxLayout, QWidget, QFileDialog, QHBoxLayout,
    QTextEdit, QComboBox, QMessageBox, QGroupBox,
    QFormLayout, QLineEdit, QSplitter, QInputDialog,
    QProgressBar, QCheckBox, QSpinBox, QGridLayout,
    QTabWidget, QScrollArea, QFrame
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

class AsymmetricPIDControls(QWidget):
    """Enhanced controls for asymmetric PID system"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Mode indicator
        self.mode_indicator = QLabel("🔄 HEATING MODE")
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
        layout.addWidget(self.mode_indicator)
        
        # Cooling PID parameters
        cooling_group = QGroupBox("❄️ Cooling PID (Conservative)")
        cooling_layout = QGridLayout()
        
        self.kp_cooling_input = QLineEdit("0.8")
        self.ki_cooling_input = QLineEdit("0.02")
        self.kd_cooling_input = QLineEdit("3.0")
        
        cooling_layout.addWidget(QLabel("Kp:"), 0, 0)
        cooling_layout.addWidget(self.kp_cooling_input, 0, 1)
        cooling_layout.addWidget(QLabel("(max 2.0)"), 0, 2)
        
        cooling_layout.addWidget(QLabel("Ki:"), 1, 0)
        cooling_layout.addWidget(self.ki_cooling_input, 1, 1)
        cooling_layout.addWidget(QLabel("(max 0.1)"), 1, 2)
        
        cooling_layout.addWidget(QLabel("Kd:"), 2, 0)
        cooling_layout.addWidget(self.kd_cooling_input, 2, 1)
        cooling_layout.addWidget(QLabel("(damping)"), 2, 2)
        
        self.set_cooling_pid_button = QPushButton("Set Cooling PID")
        self.set_cooling_pid_button.clicked.connect(self.set_cooling_pid)
        self.set_cooling_pid_button.setStyleSheet("background-color: #4dabf7; color: white; font-weight: bold;")
        cooling_layout.addWidget(self.set_cooling_pid_button, 3, 0, 1, 3)
        
        cooling_group.setLayout(cooling_layout)
        layout.addWidget(cooling_group)
        
        # Heating PID parameters
        heating_group = QGroupBox("🔥 Heating PID (Aggressive)")
        heating_layout = QGridLayout()
        
        self.kp_heating_input = QLineEdit("2.5")
        self.ki_heating_input = QLineEdit("0.2")
        self.kd_heating_input = QLineEdit("1.2")
        
        heating_layout.addWidget(QLabel("Kp:"), 0, 0)
        heating_layout.addWidget(self.kp_heating_input, 0, 1)
        heating_layout.addWidget(QLabel("(max 5.0)"), 0, 2)
        
        heating_layout.addWidget(QLabel("Ki:"), 1, 0)
        heating_layout.addWidget(self.ki_heating_input, 1, 1)
        heating_layout.addWidget(QLabel("(max 1.0)"), 1, 2)
        
        heating_layout.addWidget(QLabel("Kd:"), 2, 0)
        heating_layout.addWidget(self.kd_heating_input, 2, 1)
        heating_layout.addWidget(QLabel("(response)"), 2, 2)
        
        self.set_heating_pid_button = QPushButton("Set Heating PID")
        self.set_heating_pid_button.clicked.connect(self.set_heating_pid)
        self.set_heating_pid_button.setStyleSheet("background-color: #ff6b35; color: white; font-weight: bold;")
        heating_layout.addWidget(self.set_heating_pid_button, 3, 0, 1, 3)
        
        heating_group.setLayout(heating_layout)
        layout.addWidget(heating_group)
        
        # Safety controls
        safety_group = QGroupBox("🛡️ Safety Controls")
        safety_layout = QGridLayout()
        
        # Emergency stop
        self.emergency_stop_button = QPushButton("🚨 EMERGENCY STOP")
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
        
        # Safety parameters
        safety_layout.addWidget(QLabel("Max Cooling Rate:"), 1, 0)
        self.cooling_rate_input = QLineEdit("1.5")
        self.cooling_rate_input.setFixedWidth(60)
        safety_layout.addWidget(self.cooling_rate_input, 1, 1)
        safety_layout.addWidget(QLabel("°C/s"), 1, 2)
        
        self.set_rate_limit_button = QPushButton("Set")
        self.set_rate_limit_button.clicked.connect(self.set_cooling_rate_limit)
        self.set_rate_limit_button.setFixedWidth(40)
        safety_layout.addWidget(self.set_rate_limit_button, 1, 3)
        
        safety_layout.addWidget(QLabel("Safety Margin:"), 2, 0)
        self.safety_margin_input = QLineEdit("1.5")
        self.safety_margin_input.setFixedWidth(60)
        safety_layout.addWidget(self.safety_margin_input, 2, 1)
        safety_layout.addWidget(QLabel("°C"), 2, 2)
        
        self.set_safety_margin_button = QPushButton("Set")
        self.set_safety_margin_button.clicked.connect(self.set_safety_margin)
        self.set_safety_margin_button.setFixedWidth(40)
        safety_layout.addWidget(self.set_safety_margin_button, 2, 3)
        
        safety_group.setLayout(safety_layout)
        layout.addWidget(safety_group)
        
        # Status display
        status_group = QGroupBox("📊 System Status")
        status_layout = QGridLayout()
        
        self.current_mode_label = QLabel("Mode: Unknown")
        self.temperature_rate_label = QLabel("Rate: 0.00 °C/s")
        self.emergency_status_label = QLabel("Emergency: Clear")
        
        status_layout.addWidget(QLabel("Current Mode:"), 0, 0)
        status_layout.addWidget(self.current_mode_label, 0, 1)
        
        status_layout.addWidget(QLabel("Temp Rate:"), 1, 0)
        status_layout.addWidget(self.temperature_rate_label, 1, 1)
        
        status_layout.addWidget(QLabel("Emergency:"), 2, 0)
        status_layout.addWidget(self.emergency_status_label, 2, 1)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Asymmetric Autotune
        autotune_group = QGroupBox("🎯 Asymmetric Autotune")
        autotune_layout = QVBoxLayout()
        
        autotune_info = QLabel("Will test heating (safe) then cooling (conservative)")
        autotune_info.setStyleSheet("color: #6c757d; font-size: 10px;")
        autotune_layout.addWidget(autotune_info)
        
        self.start_asymmetric_autotune_button = QPushButton("🎯 Start Asymmetric Autotune")
        self.start_asymmetric_autotune_button.clicked.connect(self.start_asymmetric_autotune)
        self.start_asymmetric_autotune_button.setStyleSheet("background-color: #6f42c1; color: white; font-weight: bold;")
        
        self.abort_asymmetric_autotune_button = QPushButton("⛔ Abort Autotune")
        self.abort_asymmetric_autotune_button.clicked.connect(self.abort_asymmetric_autotune)
        self.abort_asymmetric_autotune_button.setStyleSheet("background-color: #fd7e14; color: white; font-weight: bold;")
        self.abort_asymmetric_autotune_button.setVisible(False)
        
        autotune_layout.addWidget(self.start_asymmetric_autotune_button)
        autotune_layout.addWidget(self.abort_asymmetric_autotune_button)
        
        autotune_group.setLayout(autotune_layout)
        layout.addWidget(autotune_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def update_status(self, data):
        """Update status displays from Arduino data"""
        try:
            # Update mode indicator
            if "cooling_mode" in data:
                if data["cooling_mode"]:
                    self.mode_indicator.setText("❄️ COOLING MODE")
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
                    self.current_mode_label.setText("❄️ Cooling")
                    self.current_mode_label.setStyleSheet("color: #4dabf7; font-weight: bold;")
                else:
                    self.mode_indicator.setText("🔥 HEATING MODE")
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
                    self.current_mode_label.setText("🔥 Heating")
                    self.current_mode_label.setStyleSheet("color: #ff6b35; font-weight: bold;")
            
            # Update temperature rate
            if "temperature_rate" in data:
                rate = float(data["temperature_rate"])
                self.temperature_rate_label.setText(f"{rate:.3f} °C/s")
                
                # Color code based on rate
                if rate < -1.0:  # Fast cooling
                    self.temperature_rate_label.setStyleSheet("color: #dc3545; font-weight: bold;")
                elif rate < -0.5:  # Moderate cooling
                    self.temperature_rate_label.setStyleSheet("color: #fd7e14; font-weight: bold;")
                elif rate > 0.5:  # Heating
                    self.temperature_rate_label.setStyleSheet("color: #ff6b35; font-weight: bold;")
                else:  # Stable
                    self.temperature_rate_label.setStyleSheet("color: #28a745; font-weight: bold;")
            
            # Update emergency status
            if "emergency_stop" in data:
                if data["emergency_stop"]:
                    self.emergency_status_label.setText("🚨 ACTIVE")
                    self.emergency_status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
                else:
                    self.emergency_status_label.setText("✅ Clear")
                    self.emergency_status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            
            # Handle asymmetric autotune status
            if "asymmetric_autotune_active" in data:
                if data["asymmetric_autotune_active"]:
                    self.start_asymmetric_autotune_button.setVisible(False)
                    self.abort_asymmetric_autotune_button.setVisible(True)
                else:
                    self.start_asymmetric_autotune_button.setVisible(True)
                    self.abort_asymmetric_autotune_button.setVisible(False)
                    
        except Exception as e:
            print(f"Status update error: {e}")
    
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
                self.parent.log(f"🔥 Heating PID set: Kp={kp:.3f}, Ki={ki:.4f}, Kd={kd:.3f}", "success")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Heating PID error: {e}")
            self.parent.log(f"❌ Invalid heating PID: {e}", "error")
    
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
                self.parent.log(f"⚠️ Cooling rate limit: {rate:.1f} °C/s", "command")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Rate limit error: {e}")
    
    def set_safety_margin(self):
        """Set safety margin"""
        try:
            margin = float(self.safety_margin_input.text())
            if not (0.5 <= margin <= 3.0):
                raise ValueError("Safety margin must be 0.5-3.0 °C")
            
            if self.parent.send_asymmetric_command("set_safety_margin", {"margin": margin}):
                self.parent.log(f"🛡️ Safety margin: {margin:.1f} °C", "command")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Safety margin error: {e}")
    
    def start_asymmetric_autotune(self):
        """Start asymmetric autotune with safety confirmation"""
        reply = QMessageBox.question(
            self, "🎯 Asymmetric Autotune",
            "Start asymmetric autotune?\n\n"
            "This will:\n"
            "1. Test heating response (safe)\n"
            "2. Test cooling response (conservative)\n"
            "3. Calculate optimal PID parameters\n\n"
            "Process will take 5-10 minutes.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.parent.send_asymmetric_command("start_asymmetric_autotune", {}):
                self.parent.log("🎯 Starting asymmetric autotune...", "command")
    
    def abort_asymmetric_autotune(self):
        """Abort asymmetric autotune"""
        if self.parent.send_asymmetric_command("abort_asymmetric_autotune", {}):
            self.parent.log("⛔ Asymmetric autotune aborted", "warning")


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
            self.ax_temp.set_title('🌡️ Temperature Monitoring', fontsize=14, fontweight='bold')
            self.ax_temp.set_ylabel('Temperature (°C)', fontsize=12)
            self.ax_temp.grid(True, alpha=0.3)
            self.ax_temp.set_facecolor('#f8f9fa')
            
            # PID subplot
            self.ax_pid = self.figure.add_subplot(gs[1])
            self.ax_pid.set_title('🎛️ PID Output', fontsize=12, fontweight='bold')
            self.ax_pid.set_ylabel('PID Output', fontsize=11)
            self.ax_pid.grid(True, alpha=0.3)
            self.ax_pid.set_facecolor('#f0f8ff')
            
            # Breath subplot
            self.ax_breath = self.figure.add_subplot(gs[2])
            self.ax_breath.set_title('🫁 Breath Frequency', fontsize=12, fontweight='bold')
            self.ax_breath.set_xlabel('Time (seconds)', fontsize=12)
            self.ax_breath.set_ylabel('BPM', fontsize=11)
            self.ax_breath.grid(True, alpha=0.3)
            self.ax_breath.set_facecolor('#fff8f0')
            
            # Initialize lines
            self.line_plate, = self.ax_temp.plot([], [], 'r-o', linewidth=3, markersize=4, 
                                               label='🔥 Cooling Plate', alpha=0.8)
            self.line_rectal, = self.ax_temp.plot([], [], 'g-s', linewidth=3, markersize=4, 
                                                label='🌡️ Rectal Probe', alpha=0.8)
            self.line_target, = self.ax_temp.plot([], [], 'b--', linewidth=2, 
                                                label='🎯 Target', alpha=0.7)
            
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
            pid_outputs = [50 * math.sin(t/10) + 20 * math.sin(t/3) for t in times]
            breath_rates = [max(5, 150 * math.exp(-t/40) + 10 + math.sin(t/4) * 8) for t in times]
            
            return {
                "time": times,
                "plate_temp": plate_temps,
                "rectal_temp": rectal_temps,
                "target_temp": target_temps,
                "pid_output": pid_outputs,
                "breath_rate": breath_rates
            }
            
        except Exception as e:
            print(f"❌ Test data error: {e}")
            return {"time": [], "plate_temp": [], "rectal_temp": [], "target_temp": [], "pid_output": [], "breath_rate": []}


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
            "target_temp": []
        }
        
        self.connection_established = False
        self.start_time = None
        self.max_graph_points = 200
        self.data_update_count = 0
        self.graph_update_count = 0
        
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
            self.create_profile_tab()
            
            # ============================================================================
            # 3. ADD THE ASYMMETRIC PID TAB HERE (in the init_ui method)
            # ============================================================================
            self.create_asymmetric_tab()
            
            print("✅ UI initialized")
            
        except Exception as e:
            print(f"❌ UI error: {e}")
            raise

    # ============================================================================
    # 4. ADD THIS NEW METHOD TO CREATE THE ASYMMETRIC TAB
    # ============================================================================
    
    def create_asymmetric_tab(self):
        """Create asymmetric PID control tab"""
        try:
            self.asymmetric_controls = AsymmetricPIDControls(self)
            self.tab_widget.addTab(self.asymmetric_controls, "🎛️ Asymmetric PID")
            print("✅ Asymmetric PID tab created")
        except Exception as e:
            print(f"❌ Asymmetric tab error: {e}")

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
        left_panel.setMaximumWidth(400)
        
        # Right panel
        right_panel = self.create_live_data_panel()
        right_panel.setMaximumWidth(350)
        
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
        self.portSelector.setFixedWidth(100)
        port_row.addWidget(self.portSelector)
        
        self.refreshButton = QPushButton("🔄")
        self.refreshButton.setFixedSize(30, 25)
        self.refreshButton.clicked.connect(self.refresh_ports)
        port_row.addWidget(self.refreshButton)
        
        self.connectButton = QPushButton("Connect")
        self.connectButton.setFixedWidth(80)
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
        self.panicButton.setFixedSize(90, 35)
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
        
        # PID PARAMETERS
        pid_group = QGroupBox("⚙️ PID Parameters")
        pid_layout = QGridLayout()
        
        self.kpInput = QLineEdit("2.0")
        self.kpInput.setFixedWidth(60)
        self.kiInput = QLineEdit("0.5")
        self.kiInput.setFixedWidth(60)
        self.kdInput = QLineEdit("1.0")
        self.kdInput.setFixedWidth(60)
        
        pid_layout.addWidget(QLabel("Kp:"), 0, 0)
        pid_layout.addWidget(self.kpInput, 0, 1)
        pid_layout.addWidget(QLabel("Ki:"), 0, 2)
        pid_layout.addWidget(self.kiInput, 0, 3)
        pid_layout.addWidget(QLabel("Kd:"), 1, 0)
        pid_layout.addWidget(self.kdInput, 1, 1)
        
        self.setPIDButton = QPushButton("Set PID")
        self.setPIDButton.clicked.connect(self.set_pid_values)
        self.setPIDButton.setStyleSheet("background-color: #007bff; color: white; font-weight: bold;")
        
        self.fetchPIDButton = QPushButton("Fetch")
        self.fetchPIDButton.clicked.connect(self.fetch_pid_parameters)
        
        pid_layout.addWidget(self.setPIDButton, 1, 2)
        pid_layout.addWidget(self.fetchPIDButton, 1, 3)
        
        pid_group.setLayout(pid_layout)
        layout.addWidget(pid_group)
        
        # TARGET TEMPERATURE
        target_group = QGroupBox("🎯 Target Temperature")
        target_layout = QHBoxLayout()
        
        self.setpointInput = QLineEdit("37.0")
        self.setpointInput.setFixedWidth(60)
        
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
        
        # PID CONTROL
        control_group = QGroupBox("🚀 PID Control")
        control_layout = QHBoxLayout()
        
        self.startPIDButton = QPushButton("▶️ START")
        self.startPIDButton.clicked.connect(lambda: self.send_and_log_cmd("pid", "start"))
        self.startPIDButton.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: white; 
                font-weight: bold; 
                padding: 8px;
                border-radius: 5px;
            }
        """)
        
        self.stopPIDButton = QPushButton("⏹️ STOP")
        self.stopPIDButton.clicked.connect(lambda: self.send_and_log_cmd("pid", "stop"))
        self.stopPIDButton.setStyleSheet("""
            QPushButton { 
                background-color: #dc3545; 
                color: white; 
                font-weight: bold; 
                padding: 8px;
                border-radius: 5px;
            }
        """)
        
        control_layout.addWidget(self.startPIDButton)
        control_layout.addWidget(self.stopPIDButton)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # ADVANCED CONTROLS
        advanced_group = QGroupBox("🔧 Advanced")
        advanced_layout = QGridLayout()
        
        self.autotuneButton = QPushButton("🎯 Autotune")
        self.autotuneButton.clicked.connect(self.start_autotune)
        
        self.abortAutotuneButton = QPushButton("⛔ Abort")
        self.abortAutotuneButton.clicked.connect(self.abort_autotune)
        self.abortAutotuneButton.setVisible(False)
        self.abortAutotuneButton.setStyleSheet("background-color: #fd7e14; color: white; font-weight: bold;")
        
        self.setMaxOutputButton = QPushButton("🔋 Max Output")
        self.setMaxOutputButton.clicked.connect(self.set_max_output_limit)
        
        self.saveEEPROMButton = QPushButton("💾 Save EEPROM")
        self.saveEEPROMButton.clicked.connect(self.save_pid_to_eeprom)
        
        self.clearFailsafeButton = QPushButton("🔓 Clear FS")
        self.clearFailsafeButton.clicked.connect(self.clear_failsafe)
        self.clearFailsafeButton.setStyleSheet("background-color: #fd7e14; color: white; font-weight: bold;")
        
        advanced_layout.addWidget(self.autotuneButton, 0, 0)
        advanced_layout.addWidget(self.abortAutotuneButton, 0, 1)
        advanced_layout.addWidget(self.setMaxOutputButton, 1, 0)
        advanced_layout.addWidget(self.saveEEPROMButton, 1, 1)
        advanced_layout.addWidget(self.clearFailsafeButton, 2, 0, 1, 2)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        return panel

    def create_live_data_panel(self):
        """Create live data display"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
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
        
        self.pidParamsLabel = QLabel("Kp: -, Ki: -, Kd: -")
        self.pidParamsLabel.setStyleSheet("font-family: 'Courier New'; font-size: 11px;")
        
        self.maxOutputLabel = QLabel("Unknown")
        self.maxOutputLabel.setStyleSheet("font-family: 'Courier New'; font-size: 11px;")
        
        self.lastUpdateLabel = QLabel("Never")
        self.lastUpdateLabel.setStyleSheet("font-family: 'Courier New'; font-size: 10px; color: #6c757d;")
        
        params_layout.addRow("PID Params:", self.pidParamsLabel)
        params_layout.addRow("Max Output:", self.maxOutputLabel)
        params_layout.addRow("Last Update:", self.lastUpdateLabel)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
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
            
            # ============================================================================
            # 6. ADD THIS LINE TO UPDATE ASYMMETRIC CONTROLS
            # ============================================================================
            if hasattr(self, 'asymmetric_controls'):
                self.asymmetric_controls.update_status(data)
            
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

            if "anal_probe_temp" in data:
                temp = float(data["anal_probe_temp"])
                self.rectalTempDisplay.setText(f"{temp:.1f}°C")

            if "pid_output" in data:
                output = float(data["pid_output"])
                self.pidOutputDisplay.setText(f"{output:.1f}")

            if "plate_target_active" in data:
                target = float(data["plate_target_active"])
                self.targetTempDisplay.setText(f"{target:.1f}°C")

            if "breath_freq_bpm" in data:
                breath = float(data["breath_freq_bpm"])
                self.breathRateDisplay.setText(f"{breath:.0f} BPM")
                
        except (ValueError, KeyError) as e:
            print(f"Display update error: {e}")

    def update_pid_displays(self, data: Dict[str, Any]):
        """Update PID parameter displays"""
        try:
            if all(key in data for key in ["pid_kp", "pid_ki", "pid_kd"]):
                kp = float(data["pid_kp"])
                ki = float(data["pid_ki"])
                kd = float(data["pid_kd"])
                
                self.kpInput.setText(f"{kp:.3f}")
                self.kiInput.setText(f"{ki:.3f}")
                self.kdInput.setText(f"{kd:.3f}")
                self.pidParamsLabel.setText(f"Kp: {kp:.3f}, Ki: {ki:.3f}, Kd: {kd:.3f}")

            if "pid_max_output" in data:
                max_output = float(data["pid_max_output"])
                self.maxOutputLabel.setText(f"{max_output:.1f}%")
                
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

            # PID status
            if "pid_output" in data:
                output = abs(float(data["pid_output"]))
                if output > 0.1:
                    self.pidStatusIndicator.setText("🟢 PID On")
                    self.pidStatusIndicator.setStyleSheet("color: #28a745; font-weight: bold;")
                else:
                    self.pidStatusIndicator.setText("⚫ PID Off")
                    self.pidStatusIndicator.setStyleSheet("color: #6c757d; font-weight: bold;")

            # Autotune
            if "autotune_active" in data:
                if data["autotune_active"]:
                    if self.autotuneButton.isVisible():
                        self.autotuneButton.setVisible(False)
                        self.abortAutotuneButton.setVisible(True)
                else:
                    if self.abortAutotuneButton.isVisible():
                        self.autotuneButton.setVisible(True)
                        self.abortAutotuneButton.setVisible(False)
                    
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

            if "response" in data:
                response_msg = str(data["response"])
                self.log(f"📥 RESPONSE: {response_msg}", "info")

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
                
                # Update inputs
                self.kpInput.setText(f"{kp:.3f}")
                self.kiInput.setText(f"{ki:.3f}")
                self.kdInput.setText(f"{kd:.3f}")
                
                # Show dialog
                QMessageBox.information(
                    self, 
                    "🎯 Autotune Complete",
                    f"New PID parameters:\n\n"
                    f"Kp: {kp:.3f}\n"
                    f"Ki: {ki:.3f}\n"
                    f"Kd: {kd:.3f}\n\n"
                    f"Click 'Set PID' to apply."
                )
                
                self.log(f"🎯 Autotune: Kp={kp:.3f}, Ki={ki:.3f}, Kd={kd:.3f}", "success")
                
        except (ValueError, KeyError) as e:
            print(f"Autotune results error: {e}")

    # ====== CONTROL METHODS ======

    def start_autotune(self):
        """Start autotune"""
        try:
            if not self.connection_established:
                self.log("❌ Not connected", "error")
                return
            
            if self.send_and_log_cmd("pid", "autotune"):
                self.log("🎯 Autotune started", "command")
                
        except Exception as e:
            self.log(f"❌ Autotune start error: {e}", "error")

    def abort_autotune(self):
        """Abort autotune"""
        try:
            if self.send_and_log_cmd("pid", "abort_autotune"):
                self.log("⛔ Autotune aborted", "warning")
                
        except Exception as e:
            self.log(f"❌ Autotune abort error: {e}", "error")

    def set_pid_values(self):
        """Set PID parameters"""
        try:
            kp = float(self.kpInput.text())
            ki = float(self.kiInput.text())
            kd = float(self.kdInput.text())
            
            # Validation
            if not (0 <= kp <= 100):
                raise ValueError("Kp must be 0-100")
            if not (0 <= ki <= 50):
                raise ValueError("Ki must be 0-50")
            if not (0 <= kd <= 50):
                raise ValueError("Kd must be 0-50")
            
            if not self.connection_established:
                self.log("❌ Not connected", "error")
                return
                
            self.serial_manager.sendSET("pid_kp", kp)
            self.serial_manager.sendSET("pid_ki", ki)
            self.serial_manager.sendSET("pid_kd", kd)
            
            self.event_logger.log_event(f"SET: PID → Kp={kp}, Ki={ki}, Kd={kd}")
            self.log(f"✅ PID set: Kp={kp}, Ki={ki}, Kd={kd}", "success")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"PID error: {e}")
            self.log(f"❌ Invalid PID: {e}", "error")
        except Exception as e:
            self.log(f"❌ PID set error: {e}", "error")

    def set_manual_setpoint(self):
        """Set target temperature"""
        try:
            value = float(self.setpointInput.text())
            
            if not (-10 <= value <= 50):
                raise ValueError("Temperature must be -10°C to 50°C")
            
            if not self.connection_established:
                self.log("❌ Not connected", "error")
                return
                
            self.serial_manager.sendSET("target_temp", value)
            self.event_logger.log_event(f"SET: target_temp → {value:.2f}°C")
            self.log(f"✅ Target set: {value:.2f}°C", "success")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Temperature error: {e}")
            self.log(f"❌ Invalid temperature: {e}", "error")
        except Exception as e:
            self.log(f"❌ Target set error: {e}", "error")

    def set_max_output_limit(self):
        """Set max output limit"""
        try:
            current_value = 20.0
            try:
                current_text = self.maxOutputLabel.text()
                if "%" in current_text:
                    current_value = float(current_text.replace("%", ""))
            except:
                pass
                
            value, ok = QInputDialog.getDouble(
                self, "Max Output Limit", 
                "Enter max output % (0–100):", 
                current_value, 0.0, 100.0, 1
            )
            
            if ok:
                if not self.connection_established:
                    self.log("❌ Not connected", "error")
                    return
                    
                self.serial_manager.sendSET("pid_max_output", value)
                self.event_logger.log_event(f"SET: pid_max_output → {value:.1f}%")
                self.log(f"⚙️ Max output: {value:.1f}%", "command")
                self.maxOutputLabel.setText(f"{value:.1f}%")
                
        except Exception as e:
            self.log(f"❌ Max output error: {e}", "error")

    def fetch_pid_parameters(self):
        """Fetch PID parameters"""
        try:
            if not self.connection_established:
                self.log("❌ Not connected", "error")
                return
                
            self.serial_manager.sendCMD("get", "pid_params")
            self.log("🔄 Fetching PID parameters...", "command")
            
            # Also get status
            QTimer.singleShot(200, lambda: self.serial_manager.sendCMD("get", "status"))
            
        except Exception as e:
            self.log(f"❌ Fetch error: {e}", "error")

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
                "target_temp": []
            }
            
            self.start_time = None
            self.graph_update_count = 0
            
            self.log("🧹 Graphs cleared", "info")
            
        except Exception as e:
            self.log(f"❌ Clear error: {e}", "error")

    # ====== PROFILE METHODS ======

    def load_profile(self):
        """Load profile"""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self, "Load Profile", "", 
                "JSON Files (*.json);;CSV Files (*.csv)"
            )
            
            if file_name:
                success = False
                if file_name.endswith('.json'):
                    success = self.profile_loader.load_profile_json(file_name)
                elif file_name.endswith('.csv'):
                    success = self.profile_loader.load_profile_csv(file_name)
                
                if success:
                    filename = os.path.basename(file_name)
                    self.profileFileLabel.setText(f"✅ {filename}")
                    self.profileFileLabel.setStyleSheet("color: #28a745; font-weight: bold;")
                    
                    # Enable buttons
                    self.startProfileButton.setEnabled(True)
                    self.pauseProfileButton.setEnabled(True)
                    self.resumeProfileButton.setEnabled(True)
                    self.stopProfileButton.setEnabled(True)
                    
                    self.log(f"✅ Profile loaded: {filename}", "success")
                else:
                    self.log(f"❌ Profile load failed", "error")
                    
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