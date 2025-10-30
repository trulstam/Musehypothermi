import sys
import json
import time
import csv
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel,
    QVBoxLayout, QWidget, QFileDialog, QHBoxLayout,
    QTextEdit, QComboBox, QMessageBox, QGroupBox,
    QFormLayout, QLineEdit, QSplitter, QInputDialog,
    QProgressBar, QCheckBox, QSpinBox, QGridLayout,
    QTabWidget, QScrollArea
)
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont, QPalette, QColor
import pyqtgraph as pg
from serial_comm import SerialManager
from event_logger import EventLogger
from profile_loader import ProfileLoader

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Musehypothermi GUI - Status Monitor v2.1")
        self.setMinimumSize(1200, 700)
        
        # Get screen size and adjust window accordingly
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1400, screen.width() - 100), min(900, screen.height() - 100))

        # Initialize UI first
        self.init_ui()

        # Initialize managers after UI
        self.serial_manager = SerialManager()
        self.serial_manager.on_data_received = self.process_incoming_data

        self.event_logger = EventLogger("gui_events")
        self.profile_loader = ProfileLoader(event_logger=self.event_logger)

        # Status request timer
        self.status_request_timer = QTimer()
        self.status_request_timer.timeout.connect(self.request_status)
        self.status_request_timer.start(3000)

        # Data storage
        self.profile_data = []
        self.last_data_time = time.time()
        self.start_time = None

        # State tracking
        self.connection_established = False
        self.autotune_in_progress = False
        self.profile_active = False
        
        # Graph mode tracking
        self.graph_mode = "live"

        # Graph data with time management
        self.graph_data = {
            "time": [],
            "plate_temp": [],
            "rectal_temp": [],
            "pid_output": [],
            "breath_rate": [],
            "target_temp": []
        }

        # Auto-sync timer
        self.sync_timer = QTimer()
        self.sync_timer.setSingleShot(True)
        self.sync_timer.timeout.connect(self.initial_sync)
        
        # Populate ports
        self.refresh_ports()

    def init_ui(self):
        # Create main widget with tabs for better organization
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Top bar - always visible
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        # Tab widget for main content
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Control Tab
        control_tab = self.create_control_tab()
        self.tab_widget.addTab(control_tab, "Control")
        
        # Monitoring Tab
        monitoring_tab = self.create_monitoring_tab()
        self.tab_widget.addTab(monitoring_tab, "Monitoring")
        
        # Profile Tab
        profile_tab = self.create_profile_tab()
        self.tab_widget.addTab(profile_tab, "Profile")

    def create_top_bar(self):
        """Compact top bar with essential controls"""
        top_widget = QWidget()
        top_widget.setMaximumHeight(60)
        top_layout = QHBoxLayout()
        top_widget.setLayout(top_layout)
        
        # Serial connection
        serial_group = QGroupBox("Connection")
        serial_group.setMaximumWidth(200)
        serial_layout = QHBoxLayout()
        
        self.portSelector = QComboBox()
        self.portSelector.setFixedWidth(60)
        
        self.refreshButton = QPushButton("↻")
        self.refreshButton.clicked.connect(self.refresh_ports)
        self.refreshButton.setFixedSize(20, 20)
        
        self.connectButton = QPushButton("Connect")
        self.connectButton.clicked.connect(self.toggle_connection)
        self.connectButton.setFixedWidth(60)
        
        serial_layout.addWidget(self.portSelector)
        serial_layout.addWidget(self.refreshButton)
        serial_layout.addWidget(self.connectButton)
        serial_group.setLayout(serial_layout)
        
        # Connection status
        self.connectionStatusLabel = QLabel("Disconnected")
        self.connectionStatusLabel.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
        
        # Key status indicators
        status_group = QGroupBox("Status")
        status_layout = QHBoxLayout()
        
        self.failsafeIndicator = QLabel("⚪ Safe")
        self.failsafeIndicator.setStyleSheet("color: green; font-size: 10px;")
        
        self.pidStatusIndicator = QLabel("⚪ PID Off")
        self.pidStatusIndicator.setStyleSheet("color: gray; font-size: 10px;")
        
        status_layout.addWidget(self.failsafeIndicator)
        status_layout.addWidget(QLabel("|"))
        status_layout.addWidget(self.pidStatusIndicator)
        status_group.setLayout(status_layout)
        
        # Emergency button
        self.panicButton = QPushButton("PANIC")
        self.panicButton.setFixedSize(60, 30)
        self.panicButton.setStyleSheet("""
            QPushButton {
                background-color: red; 
                color: white; 
                font-weight: bold; 
                font-size: 10px;
                border: none;
                border-radius: 3px;
            }
        """)
        self.panicButton.clicked.connect(self.trigger_panic)
        
        top_layout.addWidget(serial_group)
        top_layout.addWidget(self.connectionStatusLabel)
        top_layout.addWidget(status_group)
        top_layout.addStretch()
        top_layout.addWidget(self.panicButton)
        
        return top_widget

    def create_control_tab(self):
        """Control tab with PID controls and live data"""
        control_widget = QWidget()
        control_layout = QHBoxLayout()
        control_widget.setLayout(control_layout)
        
        # Left panel - Controls
        left_panel = QWidget()
        left_panel.setMaximumWidth(350)
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        # PID Parameters - Compact
        pid_group = QGroupBox("PID Parameters")
        pid_layout = QGridLayout()
        
        self.kpInput = QLineEdit("0.1")
        self.kpInput.setFixedWidth(50)
        self.kiInput = QLineEdit("0.01")
        self.kiInput.setFixedWidth(50)
        self.kdInput = QLineEdit("0.01")
        self.kdInput.setFixedWidth(50)
        
        pid_layout.addWidget(QLabel("Kp:"), 0, 0)
        pid_layout.addWidget(self.kpInput, 0, 1)
        pid_layout.addWidget(QLabel("Ki:"), 0, 2)
        pid_layout.addWidget(self.kiInput, 0, 3)
        pid_layout.addWidget(QLabel("Kd:"), 1, 0)
        pid_layout.addWidget(self.kdInput, 1, 1)
        
        self.setPIDButton = QPushButton("Set PID")
        self.setPIDButton.clicked.connect(self.set_pid_values)
        pid_layout.addWidget(self.setPIDButton, 1, 2, 1, 2)
        
        pid_group.setLayout(pid_layout)
        left_layout.addWidget(pid_group)
        
        # Target Temperature
        target_group = QGroupBox("Target Temperature")
        target_layout = QHBoxLayout()
        
        self.setpointInput = QLineEdit("37")
        self.setpointInput.setFixedWidth(50)
        
        self.setSetpointButton = QPushButton("Set")
        self.setSetpointButton.clicked.connect(self.set_manual_setpoint)
        
        target_layout.addWidget(QLabel("Target:"))
        target_layout.addWidget(self.setpointInput)
        target_layout.addWidget(QLabel("°C"))
        target_layout.addWidget(self.setSetpointButton)
        target_layout.addStretch()
        
        target_group.setLayout(target_layout)
        left_layout.addWidget(target_group)
        
        # Control Buttons
        control_group = QGroupBox("PID Control")
        control_layout = QHBoxLayout()
        
        self.startPIDButton = QPushButton("START")
        self.startPIDButton.clicked.connect(lambda: self.send_and_log_cmd("pid", "start"))
        self.startPIDButton.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        
        self.stopPIDButton = QPushButton("STOP")
        self.stopPIDButton.clicked.connect(lambda: self.send_and_log_cmd("pid", "stop"))
        self.stopPIDButton.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
        
        control_layout.addWidget(self.startPIDButton)
        control_layout.addWidget(self.stopPIDButton)
        control_group.setLayout(control_layout)
        left_layout.addWidget(control_group)
        
        # Advanced Controls - Collapsible
        advanced_group = QGroupBox("Advanced")
        advanced_layout = QHBoxLayout()
        
        self.autotuneButton = QPushButton("Autotune")
        self.autotuneButton.clicked.connect(self.start_autotune)
        
        self.fetchPIDButton = QPushButton("Fetch")
        self.fetchPIDButton.clicked.connect(self.fetch_pid_parameters)
        
        self.saveEEPROMButton = QPushButton("Save")
        self.saveEEPROMButton.clicked.connect(self.save_pid_to_eeprom)
        
        self.clearFailsafeButton = QPushButton("Clear FS")
        self.clearFailsafeButton.clicked.connect(self.clear_failsafe)
        self.clearFailsafeButton.setStyleSheet("background-color: orange; font-weight: bold;")
        
        advanced_layout.addWidget(self.autotuneButton)
        advanced_layout.addWidget(self.fetchPIDButton)
        advanced_layout.addWidget(self.saveEEPROMButton)
        advanced_layout.addWidget(self.clearFailsafeButton)
        
        advanced_group.setLayout(advanced_layout)
        left_layout.addWidget(advanced_group)
        
        left_layout.addStretch()
        
        # Right panel - Live Data
        right_panel = self.create_live_data_panel()
        
        control_layout.addWidget(left_panel)
        control_layout.addWidget(right_panel)
        
        return control_widget

    def create_live_data_panel(self):
        """Compact live data display"""
        data_group = QGroupBox("Live Data")
        data_layout = QGridLayout()
        
        # Temperature displays
        self.plateTempDisplay = QLabel("22.0°C")
        self.plateTempDisplay.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: red;")
        
        self.rectalTempDisplay = QLabel("37.0°C")
        self.rectalTempDisplay.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: green;")
        
        self.targetTempDisplay = QLabel("37.0°C")
        self.targetTempDisplay.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: blue;")
        
        self.pidOutputDisplay = QLabel("0.0")
        self.pidOutputDisplay.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: purple;")
        
        self.breathRateDisplay = QLabel("150 BPM")
        self.breathRateDisplay.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: orange;")
        
        self.lastUpdateDisplay = QLabel("Never")
        self.lastUpdateDisplay.setStyleSheet("font-family: monospace; font-size: 10px; color: gray;")
        
        # Compact grid layout
        data_layout.addWidget(QLabel("Cooling Plate:"), 0, 0)
        data_layout.addWidget(self.plateTempDisplay, 0, 1)
        
        data_layout.addWidget(QLabel("Rectal Probe:"), 1, 0)
        data_layout.addWidget(self.rectalTempDisplay, 1, 1)
        
        data_layout.addWidget(QLabel("Target:"), 2, 0)
        data_layout.addWidget(self.targetTempDisplay, 2, 1)
        
        data_layout.addWidget(QLabel("PID Output:"), 3, 0)
        data_layout.addWidget(self.pidOutputDisplay, 3, 1)
        
        data_layout.addWidget(QLabel("Breath Rate:"), 4, 0)
        data_layout.addWidget(self.breathRateDisplay, 4, 1)
        
        data_layout.addWidget(QLabel("Last Update:"), 5, 0)
        data_layout.addWidget(self.lastUpdateDisplay, 5, 1)
        
        # System status
        self.pidParamsLabel = QLabel("Kp: -, Ki: -, Kd: -")
        self.pidParamsLabel.setStyleSheet("font-size: 10px; font-family: monospace;")
        data_layout.addWidget(QLabel("PID Params:"), 6, 0)
        data_layout.addWidget(self.pidParamsLabel, 6, 1)
        
        self.maxOutputLabel = QLabel("Unknown")
        self.maxOutputLabel.setStyleSheet("font-size: 10px;")
        data_layout.addWidget(QLabel("Max Output:"), 7, 0)
        data_layout.addWidget(self.maxOutputLabel, 7, 1)
        
        data_group.setLayout(data_layout)
        return data_group

    def create_monitoring_tab(self):
        """Monitoring tab focused on graphs"""
        monitoring_widget = QWidget()
        monitoring_layout = QVBoxLayout()
        monitoring_widget.setLayout(monitoring_layout)
        
        # Graph controls - compact
        graph_controls = QHBoxLayout()
        
        self.generateTestDataButton = QPushButton("Generate Test Data")
        self.generateTestDataButton.clicked.connect(self.generate_test_data)
        self.generateTestDataButton.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        
        self.clearGraphsButton = QPushButton("Clear Graphs")
        self.clearGraphsButton.clicked.connect(self.clear_graphs)
        self.clearGraphsButton.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
        
        self.testBasicPlotButton = QPushButton("Test Plot")
        self.testBasicPlotButton.clicked.connect(self.test_basic_plot)
        self.testBasicPlotButton.setStyleSheet("QPushButton { background-color: #E91E63; color: white; }")
        
        graph_controls.addWidget(self.generateTestDataButton)
        graph_controls.addWidget(self.clearGraphsButton)
        graph_controls.addWidget(self.testBasicPlotButton)
        graph_controls.addStretch()
        
        monitoring_layout.addLayout(graph_controls)
        
        # Create graphs - optimized for laptop screens
        self.create_graphs(monitoring_layout)
        
        return monitoring_widget

    def create_graphs(self, layout):
        """Create optimized graphs for laptop screens"""
        # Temperature graph
        self.tempGraphWidget = pg.PlotWidget(title="Temperatures (°C)")
        self.tempGraphWidget.addLegend()
        self.tempGraphWidget.setLabel('bottom', 'Time (seconds)')
        self.tempGraphWidget.setLabel('left', 'Temperature (°C)')
        self.tempGraphWidget.showGrid(x=True, y=True, alpha=0.3)
        self.tempGraphWidget.setYRange(10, 45)
        self.tempGraphWidget.setXRange(0, 60)
        self.tempGraphWidget.setBackground('w')
        self.tempGraphWidget.setMinimumHeight(200)
        
        # Temperature plots
        self.temp_plot_plate = self.tempGraphWidget.plot(
            pen=pg.mkPen(color='r', width=3), 
            name="Cooling Plate",
            symbol='o', symbolSize=4, symbolBrush='r'
        )
        
        self.temp_plot_rectal = self.tempGraphWidget.plot(
            pen=pg.mkPen(color='g', width=3), 
            name="Rectal Probe",
            symbol='s', symbolSize=4, symbolBrush='g'
        )
        
        self.temp_plot_target = self.tempGraphWidget.plot(
            pen=pg.mkPen(color='b', width=2, style=Qt.DashLine), 
            name="Target"
        )
        
        # Combined PID and Breath graph for space efficiency
        self.combinedGraphWidget = pg.PlotWidget(title="PID Output & Breath Rate")
        self.combinedGraphWidget.addLegend()
        self.combinedGraphWidget.setLabel('bottom', 'Time (seconds)')
        self.combinedGraphWidget.setLabel('left', 'Value')
        self.combinedGraphWidget.showGrid(x=True, y=True, alpha=0.3)
        self.combinedGraphWidget.setYRange(-50, 200)
        self.combinedGraphWidget.setXRange(0, 60)
        self.combinedGraphWidget.setBackground('w')
        self.combinedGraphWidget.setMinimumHeight(200)
        
        self.pid_plot = self.combinedGraphWidget.plot(
            pen=pg.mkPen(color='purple', width=3), 
            name="PID Output",
            symbol='t', symbolSize=4, symbolBrush='purple'
        )
        
        self.breath_plot = self.combinedGraphWidget.plot(
            pen=pg.mkPen(color='orange', width=3), 
            name="Breath Rate (BPM)",
            symbol='d', symbolSize=4, symbolBrush='orange'
        )
        
        layout.addWidget(self.tempGraphWidget)
        layout.addWidget(self.combinedGraphWidget)

    def create_profile_tab(self):
        """Profile management tab"""
        profile_widget = QWidget()
        profile_layout = QVBoxLayout()
        profile_widget.setLayout(profile_layout)
        
        # Profile loading
        load_group = QGroupBox("Profile Management")
        load_layout = QHBoxLayout()
        
        self.loadProfileButton = QPushButton("Load Profile")
        self.loadProfileButton.clicked.connect(self.load_profile)
        
        self.profileFileLabel = QLabel("No profile loaded")
        self.profileFileLabel.setStyleSheet("font-style: italic; color: gray;")
        
        load_layout.addWidget(self.loadProfileButton)
        load_layout.addWidget(self.profileFileLabel)
        load_layout.addStretch()
        
        load_group.setLayout(load_layout)
        profile_layout.addWidget(load_group)
        
        # Profile controls
        control_group = QGroupBox("Profile Control")
        control_layout = QHBoxLayout()
        
        self.startProfileButton = QPushButton("Start")
        self.startProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "start"))
        self.startProfileButton.setEnabled(False)
        
        self.pauseProfileButton = QPushButton("Pause")
        self.pauseProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "pause"))
        self.pauseProfileButton.setEnabled(False)
        
        self.resumeProfileButton = QPushButton("Resume")
        self.resumeProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "resume"))
        self.resumeProfileButton.setEnabled(False)
        
        self.stopProfileButton = QPushButton("Stop")
        self.stopProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "stop"))
        self.stopProfileButton.setEnabled(False)
        
        control_layout.addWidget(self.startProfileButton)
        control_layout.addWidget(self.pauseProfileButton)
        control_layout.addWidget(self.resumeProfileButton)
        control_layout.addWidget(self.stopProfileButton)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        profile_layout.addWidget(control_group)
        
        # Progress indicator
        self.profileProgressBar = QProgressBar()
        self.profileProgressBar.setVisible(False)
        profile_layout.addWidget(self.profileProgressBar)
        
        # Event log in profile tab
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout()
        
        log_controls = QHBoxLayout()
        self.clearLogButton = QPushButton("Clear Log")
        self.clearLogButton.clicked.connect(lambda: self.logBox.clear())
        
        self.autoScrollCheckbox = QCheckBox("Auto-scroll")
        self.autoScrollCheckbox.setChecked(True)
        
        log_controls.addWidget(self.clearLogButton)
        log_controls.addWidget(self.autoScrollCheckbox)
        log_controls.addStretch()
        
        self.logBox = QTextEdit()
        self.logBox.setReadOnly(True)
        self.logBox.setMaximumHeight(250)
        self.logBox.setFont(QFont("Courier", 9))
        
        log_layout.addLayout(log_controls)
        log_layout.addWidget(self.logBox)
        log_group.setLayout(log_layout)
        
        profile_layout.addWidget(log_group)
        profile_layout.addStretch()
        
        return profile_widget

    # Add the abortAutotuneButton for autotune functionality
    def start_autotune(self):
        """Start PID autotune"""
        if not self.serial_manager.is_connected():
            self.log("❌ Not connected", "error")
            return
            
        # Change button to abort during autotune
        self.autotuneButton.setText("Abort")
        self.autotuneButton.clicked.disconnect()
        self.autotuneButton.clicked.connect(self.abort_autotune)
        self.autotuneButton.setStyleSheet("background-color: orange; font-weight: bold;")
        
        self.send_and_log_cmd("pid", "autotune")
        self.log("🔧 Starting PID autotune...", "command")

    def abort_autotune(self):
        """Abort PID autotune"""
        self.send_and_log_cmd("pid", "abort_autotune")
        
        # Reset button
        self.autotuneButton.setText("Autotune")
        self.autotuneButton.clicked.disconnect()
        self.autotuneButton.clicked.connect(self.start_autotune)
        self.autotuneButton.setStyleSheet("")
        
        self.log("⏹ Autotune aborted", "warning")

    # Include all the other methods from the previous implementation
    def test_basic_plot(self):
        """Test absolute basic plotting"""
        try:
            print("BASIC PLOT TEST - Testing red dots")
            
            # Clear first
            self.temp_plot_plate.clear()
            
            # Super simple data
            x_data = [0, 1, 2, 3, 4, 5]
            y_data = [20, 25, 30, 35, 40, 45]
            
            # Plot with visible red pen and symbols
            self.temp_plot_plate.setData(x_data, y_data, pen='r', symbol='o', symbolBrush='r', symbolSize=8)
            
            # Set range to see the data
            self.tempGraphWidget.setXRange(-1, 6)
            self.tempGraphWidget.setYRange(15, 50)
            
            print("✅ Basic plot test complete - should see red dots and line")
            self.log("✅ Basic plot test - check for red dots in temperature graph", "success")
            
        except Exception as e:
            print(f"❌ Basic plot error: {e}")
            self.log(f"❌ Basic plot error: {e}", "error")

    def generate_test_data(self):
        """Generate test data to populate graphs"""
        try:
            print("Generating test data...")
            self.clear_graphs()
            
            # Create meaningful test data
            import math
            
            times = []
            plate_temps = []
            rectal_temps = []
            pid_outputs = []
            breath_rates = []
            target_temps = []
            
            # Generate 60 seconds of simulated data
            for i in range(60):
                times.append(i)
                
                # Simulate cooling plate temperature (starts at 37, cools to 20)
                plate_temp = 37 - (17 * (1 - math.exp(-i/20))) + math.sin(i/5) * 0.5
                plate_temps.append(plate_temp)
                
                # Simulate rectal temperature (follows plate but slower)
                rectal_temp = 37 - (12 * (1 - math.exp(-i/30))) + math.sin(i/8) * 0.3
                rectal_temps.append(rectal_temp)
                
                # Simulate PID output
                pid_output = -50 + 30 * math.sin(i/10) + math.sin(i/3) * 10
                pid_outputs.append(pid_output)
                
                # Simulate breath rate (decreases with temperature)
                breath_rate = 150 * math.exp(-i/40) + 10 + math.sin(i/4) * 5
                breath_rates.append(max(0, breath_rate))
                
                # Target temperature
                if i < 20:
                    target_temps.append(37)
                elif i < 40:
                    target_temps.append(25)
                else:
                    target_temps.append(20)
            
            # Update graph data
            self.graph_data = {
                "time": times,
                "plate_temp": plate_temps,
                "rectal_temp": rectal_temps,
                "pid_output": pid_outputs,
                "breath_rate": breath_rates,
                "target_temp": target_temps
            }
            
            # Plot the data
            self.update_graphs()
            
            # Update displays with latest values
            self.plateTempDisplay.setText(f"{plate_temps[-1]:.1f}°C")
            self.rectalTempDisplay.setText(f"{rectal_temps[-1]:.1f}°C")
            self.pidOutputDisplay.setText(f"{pid_outputs[-1]:.1f}")
            self.targetTempDisplay.setText(f"{target_temps[-1]:.1f}°C")
            self.breathRateDisplay.setText(f"{breath_rates[-1]:.0f} BPM")
            
            self.log("✅ Test data generated successfully", "success")
            
        except Exception as e:
            print(f"❌ Generate test data error: {e}")
            self.log(f"❌ Generate test data error: {e}", "error")

    def clear_graphs(self):
        """Clear all graph data"""
        try:
            print("Clearing graphs...")
            
            # Clear plot data
            self.temp_plot_plate.clear()
            self.temp_plot_rectal.clear()
            self.temp_plot_target.clear()
            self.pid_plot.clear()
            self.breath_plot.clear()
            
            # Clear internal data
            self.graph_data = {
                "time": [],
                "plate_temp": [],
                "rectal_temp": [],
                "pid_output": [],
                "breath_rate": [],
                "target_temp": []
            }
            
            self.log("🧹 Graphs cleared", "info")
            
        except Exception as e:
            print(f"❌ Clear graphs error: {e}")
            self.log(f"❌ Clear graphs error: {e}", "error")

    def update_graphs(self):
        """Update all graphs with current data"""
        try:
            if not self.graph_data["time"]:
                return
                
            # Update temperature graph
            self.temp_plot_plate.setData(self.graph_data["time"], self.graph_data["plate_temp"])
            self.temp_plot_rectal.setData(self.graph_data["time"], self.graph_data["rectal_temp"])
            self.temp_plot_target.setData(self.graph_data["time"], self.graph_data["target_temp"])
            
            # Update combined graph
            self.pid_plot.setData(self.graph_data["time"], self.graph_data["pid_output"])
            self.breath_plot.setData(self.graph_data["time"], self.graph_data["breath_rate"])
            
            # Auto-scale X axis to show last 60 seconds
            if len(self.graph_data["time"]) > 60:
                x_min = self.graph_data["time"][-60]
                x_max = self.graph_data["time"][-1]
                self.tempGraphWidget.setXRange(x_min, x_max + 5)
                self.combinedGraphWidget.setXRange(x_min, x_max + 5)
            
        except Exception as e:
            print(f"❌ Update graphs error: {e}")

    def send_and_log_cmd(self, action, state):
        """Send command and log it"""
        if not self.serial_manager.is_connected():
            self.log("❌ Not connected - cannot send command", "error")
            return
            
        self.serial_manager.sendCMD(action, state)
        self.event_logger.log_event(f"CMD: {action} -> {state}")
        self.log(f"🛰️ Sent CMD: {action} = {state}", "command")

    def log(self, message, log_type="info"):
        """Enhanced logging with types"""
        timestamp = time.strftime("%H:%M:%S")
        
        # Color coding based on log type
        if log_type == "error":
            color_style = "color: red;"
        elif log_type == "success":
            color_style = "color: green;"
        elif log_type == "command":
            color_style = "color: blue;"
        elif log_type == "warning":
            color_style = "color: orange;"
        else:
            color_style = "color: black;"
        
        formatted_message = f'<span style="{color_style}">[{timestamp}] {message}</span>'
        
        try:
            self.logBox.append(formatted_message)
            if self.autoScrollCheckbox.isChecked():
                scrollbar = self.logBox.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            # Fallback to plain text if HTML fails
            self.logBox.append(f"[{timestamp}] {message}")
        
        print(f"LOG: {message}")

    def process_incoming_data(self, data):
        """Process incoming data from Arduino"""
        if not data:
            return

        try:
            # Update live data displays
            if "cooling_plate_temp" in data:
                temp = data["cooling_plate_temp"]
                self.plateTempDisplay.setText(f"{temp:.1f}°C")

            if "anal_probe_temp" in data:
                temp = data["anal_probe_temp"]
                self.rectalTempDisplay.setText(f"{temp:.1f}°C")

            if "pid_output" in data:
                output = data["pid_output"]
                self.pidOutputDisplay.setText(f"{output:.1f}")

            if "plate_target_active" in data:
                target = data["plate_target_active"]
                self.targetTempDisplay.setText(f"{target:.1f}°C")

            if "breath_freq_bpm" in data:
                breath = data["breath_freq_bpm"]
                self.breathRateDisplay.setText(f"{breath:.0f} BPM")

            # Update PID parameters display
            if "pid_kp" in data and "pid_ki" in data and "pid_kd" in data:
                kp = data["pid_kp"]
                ki = data["pid_ki"]
                kd = data["pid_kd"]
                self.kpInput.setText(str(kp))
                self.kiInput.setText(str(ki))
                self.kdInput.setText(str(kd))
                self.pidParamsLabel.setText(f"Kp: {kp}, Ki: {ki}, Kd: {kd}")

            # Update status displays
            if "failsafe_active" in data:
                failsafe = data["failsafe_active"]
                if failsafe:
                    self.failsafeIndicator.setText("🔴 FAILSAFE")
                    self.failsafeIndicator.setStyleSheet("color: red; font-weight: bold;")
                else:
                    self.failsafeIndicator.setText("🟢 Safe")
                    self.failsafeIndicator.setStyleSheet("color: green; font-weight: bold;")

            # Update PID status in top bar
            if "pid_output" in data:
                output = data["pid_output"]
                if abs(output) > 0.1:
                    self.pidStatusIndicator.setText("🟢 PID On")
                    self.pidStatusIndicator.setStyleSheet("color: green; font-weight: bold;")
                else:
                    self.pidStatusIndicator.setText("⚪ PID Off")
                    self.pidStatusIndicator.setStyleSheet("color: gray;")

            if "autotune_active" in data:
                is_active = data["autotune_active"]
                if is_active and self.autotuneButton.text() == "Autotune":
                    # Switch to abort mode
                    self.autotuneButton.setText("Abort")
                    self.autotuneButton.clicked.disconnect()
                    self.autotuneButton.clicked.connect(self.abort_autotune)
                    self.autotuneButton.setStyleSheet("background-color: orange; font-weight: bold;")
                elif not is_active and self.autotuneButton.text() == "Abort":
                    # Switch back to start mode
                    self.autotuneButton.setText("Autotune")
                    self.autotuneButton.clicked.disconnect()
                    self.autotuneButton.clicked.connect(self.start_autotune)
                    self.autotuneButton.setStyleSheet("")

            if "pid_max_output" in data:
                max_output = data["pid_max_output"]
                self.maxOutputLabel.setText(f"{max_output:.1f}%")

            # Update graph data if we're in live mode
            if self.graph_mode == "live":
                now = time.time()
                if not self.start_time:
                    self.start_time = now
                
                elapsed = now - self.start_time
                self.graph_data["time"].append(elapsed)
                
                self.graph_data["plate_temp"].append(data.get("cooling_plate_temp", self.graph_data["plate_temp"][-1] if self.graph_data["plate_temp"] else 22.0))
                self.graph_data["rectal_temp"].append(data.get("anal_probe_temp", self.graph_data["rectal_temp"][-1] if self.graph_data["rectal_temp"] else 37.0))
                self.graph_data["pid_output"].append(data.get("pid_output", self.graph_data["pid_output"][-1] if self.graph_data["pid_output"] else 0.0))
                self.graph_data["breath_rate"].append(data.get("breath_freq_bpm", self.graph_data["breath_rate"][-1] if self.graph_data["breath_rate"] else 150.0))
                self.graph_data["target_temp"].append(data.get("plate_target_active", self.graph_data["target_temp"][-1] if self.graph_data["target_temp"] else 37.0))
                
                # Limit data to last 200 points
                for key in self.graph_data:
                    if len(self.graph_data[key]) > 200:
                        self.graph_data[key] = self.graph_data[key][-200:]
                
                self.update_graphs()

            # Update last update time
            self.lastUpdateDisplay.setText(time.strftime("%H:%M:%S"))

            # Handle events
            if "event" in data:
                event_msg = data["event"]
                self.log(f"📢 EVENT: {event_msg}", "info")
                self.event_logger.log_event(event_msg)

        except Exception as e:
            self.log(f"❌ Error processing data: {e}", "error")
            print(f"Data processing error: {e}")

    def fetch_pid_parameters(self):
        """Fetch PID parameters from Arduino"""
        if not self.serial_manager.is_connected():
            self.log("❌ Not connected", "error")
            return
            
        self.serial_manager.sendCMD("get", "pid_params")
        self.log("🔄 Fetching PID parameters...", "command")

    def set_max_output_limit(self):
        """Set maximum PID output limit"""
        value, ok = QInputDialog.getDouble(
            self, "Set Max Output Limit", 
            "Enter max output % (0–100):", 
            20.0, 0.0, 100.0, 1
        )
        if ok:
            self.serial_manager.sendSET("pid_max_output", value)
            self.event_logger.log_event(f"SET: pid_max_output -> {value:.1f}%")
            self.log(f"⚙️ Max output limit set to {value:.1f}%", "command")

    def save_pid_to_eeprom(self):
        """Save PID parameters to EEPROM"""
        if not self.serial_manager.is_connected():
            self.log("❌ Not connected", "error")
            return
            
        self.serial_manager.sendCMD("save_eeprom", "")
        self.event_logger.log_event("CMD: save_eeprom")
        self.log("💾 PID values saved to EEPROM", "success")

    def set_pid_values(self):
        """Set PID values manually"""
        try:
            kp = float(self.kpInput.text())
            ki = float(self.kiInput.text())
            kd = float(self.kdInput.text())
            
            if not self.serial_manager.is_connected():
                self.log("❌ Not connected", "error")
                return
                
            self.serial_manager.sendSET("pid_kp", kp)
            self.serial_manager.sendSET("pid_ki", ki)
            self.serial_manager.sendSET("pid_kd", kd)
            
            self.event_logger.log_event(f"SET: PID -> Kp={kp}, Ki={ki}, Kd={kd}")
            self.log(f"✅ Set PID: Kp={kp}, Ki={ki}, Kd={kd}", "success")
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for PID parameters.")
            self.log("❌ Invalid PID values entered", "error")

    def set_manual_setpoint(self):
        """Set manual temperature setpoint"""
        try:
            value = float(self.setpointInput.text())
            
            if not self.serial_manager.is_connected():
                self.log("❌ Not connected", "error")
                return
                
            self.serial_manager.sendSET("target_temp", value)
            self.event_logger.log_event(f"SET: target_temp -> {value:.2f} C")
            self.log(f"✅ Manual setpoint set to {value:.2f} °C", "success")
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for target temperature.")
            self.log("❌ Invalid temperature value entered", "error")

    def load_profile(self):
        """Load temperature profile from file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Profile", "", 
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        if file_name:
            try:
                if file_name.endswith(".json"):
                    success = self.profile_loader.load_profile_json(file_name)
                else:
                    success = self.profile_loader.load_profile_csv(file_name)
                
                if success:
                    self.profile_data = self.profile_loader.get_profile()
                    filename = os.path.basename(file_name)
                    self.profileFileLabel.setText(filename)
                    self.profileFileLabel.setStyleSheet("color: green; font-weight: bold;")
                    
                    # Enable profile buttons
                    self.startProfileButton.setEnabled(True)
                    self.pauseProfileButton.setEnabled(True)
                    self.resumeProfileButton.setEnabled(True)
                    self.stopProfileButton.setEnabled(True)
                    
                    self.log(f"✅ Loaded profile: {filename}", "success")
                else:
                    self.log(f"❌ Failed to load profile: {file_name}", "error")
                    
            except Exception as e:
                self.log(f"❌ Profile load error: {e}", "error")

    def request_status(self):
        """Request status from Arduino"""
        if self.serial_manager.is_connected():
            self.serial_manager.sendCMD("get", "status")

    def trigger_panic(self):
        """Trigger emergency panic"""
        if not self.serial_manager.is_connected():
            self.log("❌ Not connected", "error")
            return

        self.serial_manager.sendCMD("panic", "")
        self.event_logger.log_event("CMD: panic triggered")
        self.log("🚨 PANIC TRIGGERED!", "error")
        panic_box = QMessageBox(self)
        panic_box.setIcon(QMessageBox.Critical)
        panic_box.setWindowTitle("DON'T PANIC")
        panic_box.setTextFormat(Qt.RichText)
        panic_box.setText(
            "<h2 style='color:#b22222;'>DON'T PANIC</h2>"
            "<p>Panic-knappen er trykket. Finn frem håndkleet ditt og hold roen.</p>"
        )
        panic_box.setInformativeText("Nødstoppsignalet ble sendt umiddelbart.")
        panic_box.setStandardButtons(QMessageBox.Ok)
        panic_box.exec()

    def clear_failsafe(self):
        """Clear failsafe condition"""
        if not self.serial_manager.is_connected():
            self.log("❌ Not connected", "error")
            return
            
        self.serial_manager.sendCMD("failsafe_clear", "")
        self.event_logger.log_event("CMD: failsafe_clear sent")
        self.log("🔧 Sent failsafe clear command", "command")

    def refresh_ports(self):
        """Refresh available serial ports"""
        self.portSelector.clear()
        ports = self.serial_manager.list_ports()
        self.portSelector.addItems(ports)
        self.log(f"🔄 Found {len(ports)} serial ports", "info")

    def toggle_connection(self):
        """Toggle serial connection"""
        if self.serial_manager.is_connected():
            self.serial_manager.disconnect()
            self.connectButton.setText("Connect")
            self.connectionStatusLabel.setText("Disconnected")
            self.connectionStatusLabel.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
            self.log("🔌 Disconnected", "info")
            self.event_logger.log_event("Disconnected")
            self.connection_established = False
        else:
            port = self.portSelector.currentText()
            if not port:
                self.log("❌ No port selected", "error")
                return
                
            if self.serial_manager.connect(port):
                self.connectButton.setText("Disconnect")
                self.connectionStatusLabel.setText(f"Connected to {port}")
                self.connectionStatusLabel.setStyleSheet("color: green; font-weight: bold; font-size: 10px;")
                self.log(f"🔌 Connected to {port}", "success")
                self.event_logger.log_event(f"Connected to {port}")
                self.connection_established = True
                
                # Start sync timer
                self.sync_timer.start(1000)
            else:
                self.log(f"❌ Failed to connect to {port}", "error")

    def initial_sync(self):
        """Initial synchronization after connection"""
        if self.serial_manager.is_connected():
            self.log("🔄 Syncing with Arduino...", "info")
            QTimer.singleShot(500, self.request_status)
            QTimer.singleShot(1000, self.fetch_pid_parameters)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Apply dark theme
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())