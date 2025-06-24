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
    QProgressBar, QCheckBox, QSpinBox, QGridLayout
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
        self.setWindowTitle("Musehypothermi GUI - Status Monitor v2.0")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

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
        # Main layout with splitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel
        left_widget = self.create_left_panel()
        left_widget.setMinimumWidth(500)
        main_splitter.addWidget(left_widget)
        
        # Right panel
        right_widget = self.create_right_panel()
        right_widget.setMinimumWidth(350)
        main_splitter.addWidget(right_widget)
        
        # Set splitter proportions
        main_splitter.setSizes([700, 450])
        
        # Graph panel
        graph_widget = self.create_graph_panel()
        
        # Main container
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.addWidget(main_splitter, 2)
        container_layout.addWidget(graph_widget, 1)
        container.setLayout(container_layout)
        
        self.setCentralWidget(container)

    def create_left_panel(self):
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(8, 8, 8, 8)

        # TOP ROW: Serial + Status
        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(10)
        
        serial_section = self.create_serial_section()
        serial_section.setMaximumWidth(250)
        
        status_section = self.create_status_section()
        status_section.setMaximumWidth(300)
        
        top_row_layout.addWidget(serial_section)
        top_row_layout.addWidget(status_section)
        top_row_layout.addStretch()
        
        left_layout.addLayout(top_row_layout)
        
        # PID control section
        pid_section = self.create_pid_section()
        pid_section.setMinimumHeight(300)
        left_layout.addWidget(pid_section)
        
        # Profile + Emergency
        bottom_row_layout = QHBoxLayout()
        bottom_row_layout.setSpacing(10)
        
        profile_section = self.create_profile_section()
        profile_section.setMaximumWidth(300)
        
        emergency_section = self.create_emergency_section()
        emergency_section.setMaximumWidth(250)
        
        bottom_row_layout.addWidget(profile_section)
        bottom_row_layout.addWidget(emergency_section)
        bottom_row_layout.addStretch()
        
        left_layout.addLayout(bottom_row_layout)
        left_layout.addStretch(1)
        
        left_widget.setLayout(left_layout)
        return left_widget

    def create_serial_section(self):
        group = QGroupBox("Serial Connection")
        group.setMaximumHeight(100)
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Port selection
        port_layout = QHBoxLayout()
        port_layout.setSpacing(5)
        
        self.portSelector = QComboBox()
        self.portSelector.setFixedWidth(80)
        
        self.refreshButton = QPushButton("↻")
        self.refreshButton.clicked.connect(self.refresh_ports)
        self.refreshButton.setFixedSize(25, 25)
        self.refreshButton.setToolTip("Refresh ports")
        
        self.connectButton = QPushButton("Connect")
        self.connectButton.clicked.connect(self.toggle_connection)
        self.connectButton.setFixedWidth(70)
        self.connectButton.setFixedHeight(25)
        
        port_layout.addWidget(QLabel("Port:"))
        port_layout.addWidget(self.portSelector)
        port_layout.addWidget(self.refreshButton)
        port_layout.addWidget(self.connectButton)
        port_layout.addStretch()
        
        layout.addLayout(port_layout)
        
        # Connection status
        self.connectionStatusLabel = QLabel("Disconnected")
        self.connectionStatusLabel.setStyleSheet("color: red; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.connectionStatusLabel)
        
        group.setLayout(layout)
        return group

    def create_status_section(self):
        group = QGroupBox("System Status")
        group.setMaximumHeight(100)
        layout = QFormLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Status labels
        self.failsafeLabel = QLabel("Unknown")
        self.failsafeLabel.setStyleSheet("font-size: 11px;")
        
        self.profileStatusLabel = QLabel("Inactive")
        self.profileStatusLabel.setStyleSheet("font-size: 11px;")
        
        self.autotuneStatusLabel = QLabel("Idle")
        self.autotuneStatusLabel.setStyleSheet("font-size: 11px;")
        
        self.maxOutputLabel = QLabel("Unknown")
        self.maxOutputLabel.setStyleSheet("font-size: 11px;")
        
        self.pidParamsLabel = QLabel("Kp: -, Ki: -, Kd: -")
        self.pidParamsLabel.setStyleSheet("font-size: 10px; font-family: monospace;")
        
        layout.addRow("Failsafe:", self.failsafeLabel)
        layout.addRow("Profile:", self.profileStatusLabel)
        layout.addRow("Autotune:", self.autotuneStatusLabel)
        layout.addRow("Max Out:", self.maxOutputLabel)
        layout.addRow("PID:", self.pidParamsLabel)
        
        group.setLayout(layout)
        return group

    def create_pid_section(self):
        group = QGroupBox("PID Control")
        group.setMinimumHeight(280)
        group.setMaximumHeight(320)
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # PID Parameters + Target
        params_target_layout = QHBoxLayout()
        params_target_layout.setSpacing(10)
        
        # PID Parameters
        pid_params_group = QGroupBox("PID Parameters")
        pid_params_group.setMaximumWidth(300)
        pid_layout = QGridLayout()
        pid_layout.setSpacing(5)
        
        self.kpInput = QLineEdit("0.1")
        self.kpInput.setFixedWidth(50)
        self.kpInput.setFixedHeight(22)
        
        self.kiInput = QLineEdit("0.01")
        self.kiInput.setFixedWidth(50)
        self.kiInput.setFixedHeight(22)
        
        self.kdInput = QLineEdit("0.01")
        self.kdInput.setFixedWidth(50)
        self.kdInput.setFixedHeight(22)
        
        pid_layout.addWidget(QLabel("Kp:"), 0, 0)
        pid_layout.addWidget(self.kpInput, 0, 1)
        pid_layout.addWidget(QLabel("Ki:"), 0, 2)
        pid_layout.addWidget(self.kiInput, 0, 3)
        pid_layout.addWidget(QLabel("Kd:"), 1, 0)
        pid_layout.addWidget(self.kdInput, 1, 1)
        
        self.setPIDButton = QPushButton("Set")
        self.setPIDButton.setFixedSize(60, 22)
        self.setPIDButton.clicked.connect(self.set_pid_values)
        pid_layout.addWidget(self.setPIDButton, 1, 2, 1, 2)
        
        pid_params_group.setLayout(pid_layout)
        params_target_layout.addWidget(pid_params_group)
        
        # Target Temperature
        target_group = QGroupBox("Target")
        target_group.setMaximumWidth(200)
        target_layout = QHBoxLayout()
        target_layout.setSpacing(5)
        
        self.setpointInput = QLineEdit("37")
        self.setpointInput.setFixedWidth(50)
        self.setpointInput.setFixedHeight(22)
        
        self.setSetpointButton = QPushButton("Set")
        self.setSetpointButton.setFixedSize(50, 22)
        self.setSetpointButton.clicked.connect(self.set_manual_setpoint)
        
        target_layout.addWidget(QLabel("°C:"))
        target_layout.addWidget(self.setpointInput)
        target_layout.addWidget(self.setSetpointButton)
        target_layout.addStretch()
        
        target_group.setLayout(target_layout)
        params_target_layout.addWidget(target_group)
        params_target_layout.addStretch()
        
        layout.addLayout(params_target_layout)
        
        # PID Control Buttons
        control_group = QGroupBox("Control")
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)
        
        self.startPIDButton = QPushButton("▶ START")
        self.startPIDButton.clicked.connect(lambda: self.send_and_log_cmd("pid", "start"))
        self.startPIDButton.setFixedHeight(35)
        self.startPIDButton.setFixedWidth(80)
        self.startPIDButton.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold; 
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        
        self.stopPIDButton = QPushButton("⏹ STOP")
        self.stopPIDButton.clicked.connect(lambda: self.send_and_log_cmd("pid", "stop"))
        self.stopPIDButton.setFixedHeight(35)
        self.stopPIDButton.setFixedWidth(80)
        self.stopPIDButton.setStyleSheet("""
            QPushButton { 
                background-color: #f44336; 
                color: white; 
                font-weight: bold; 
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #da190b; }
        """)
        
        control_layout.addWidget(self.startPIDButton)
        control_layout.addWidget(self.stopPIDButton)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Autotune + Advanced
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)
        
        # Autotune
        autotune_group = QGroupBox("Autotune")
        autotune_group.setMaximumWidth(200)
        autotune_layout = QHBoxLayout()
        autotune_layout.setSpacing(5)
        
        self.autotuneButton = QPushButton("Start")
        self.autotuneButton.clicked.connect(self.start_autotune)
        self.autotuneButton.setFixedSize(60, 25)
        
        self.abortAutotuneButton = QPushButton("Abort")
        self.abortAutotuneButton.clicked.connect(self.abort_autotune)
        self.abortAutotuneButton.setVisible(False)
        self.abortAutotuneButton.setFixedSize(60, 25)
        self.abortAutotuneButton.setStyleSheet("background-color: orange; font-weight: bold;")
        
        autotune_layout.addWidget(self.autotuneButton)
        autotune_layout.addWidget(self.abortAutotuneButton)
        autotune_layout.addStretch()
        
        autotune_group.setLayout(autotune_layout)
        bottom_layout.addWidget(autotune_group)
        
        # Advanced
        advanced_group = QGroupBox("Advanced")
        advanced_group.setMaximumWidth(250)
        advanced_layout = QHBoxLayout()
        advanced_layout.setSpacing(5)
        
        self.setMaxOutputButton = QPushButton("Max")
        self.setMaxOutputButton.clicked.connect(self.set_max_output_limit)
        self.setMaxOutputButton.setFixedSize(45, 25)
        
        self.saveEEPROMButton = QPushButton("Save")
        self.saveEEPROMButton.clicked.connect(self.save_pid_to_eeprom)
        self.saveEEPROMButton.setFixedSize(45, 25)
        
        self.fetchPIDButton = QPushButton("Fetch")
        self.fetchPIDButton.clicked.connect(self.fetch_pid_parameters)
        self.fetchPIDButton.setFixedSize(45, 25)
        
        advanced_layout.addWidget(self.setMaxOutputButton)
        advanced_layout.addWidget(self.saveEEPROMButton)
        advanced_layout.addWidget(self.fetchPIDButton)
        advanced_layout.addStretch()
        
        advanced_group.setLayout(advanced_layout)
        bottom_layout.addWidget(advanced_group)
        bottom_layout.addStretch()
        
        layout.addLayout(bottom_layout)
        
        group.setLayout(layout)
        return group

    def create_profile_section(self):
        group = QGroupBox("Profile Control")
        group.setMaximumHeight(100)
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Profile loading
        load_layout = QHBoxLayout()
        load_layout.setSpacing(5)
        
        self.loadProfileButton = QPushButton("Load")
        self.loadProfileButton.clicked.connect(self.load_profile)
        self.loadProfileButton.setFixedSize(50, 25)
        
        self.profileFileLabel = QLabel("No profile")
        self.profileFileLabel.setStyleSheet("font-style: italic; color: gray; font-size: 11px;")
        
        load_layout.addWidget(self.loadProfileButton)
        load_layout.addWidget(self.profileFileLabel)
        load_layout.addStretch()
        
        layout.addLayout(load_layout)
        
        # Profile control buttons
        control_layout = QHBoxLayout()
        control_layout.setSpacing(5)
        
        self.startProfileButton = QPushButton("Start")
        self.startProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "start"))
        self.startProfileButton.setEnabled(False)
        self.startProfileButton.setFixedSize(50, 25)
        
        self.pauseProfileButton = QPushButton("Pause")
        self.pauseProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "pause"))
        self.pauseProfileButton.setEnabled(False)
        self.pauseProfileButton.setFixedSize(50, 25)
        
        self.resumeProfileButton = QPushButton("Resume")
        self.resumeProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "resume"))
        self.resumeProfileButton.setEnabled(False)
        self.resumeProfileButton.setFixedSize(55, 25)
        
        self.stopProfileButton = QPushButton("Stop")
        self.stopProfileButton.clicked.connect(lambda: self.send_and_log_cmd("profile", "stop"))
        self.stopProfileButton.setEnabled(False)
        self.stopProfileButton.setFixedSize(50, 25)
        
        control_layout.addWidget(self.startProfileButton)
        control_layout.addWidget(self.pauseProfileButton)
        control_layout.addWidget(self.resumeProfileButton)
        control_layout.addWidget(self.stopProfileButton)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # Progress bar
        self.profileProgressBar = QProgressBar()
        self.profileProgressBar.setVisible(False)
        self.profileProgressBar.setFixedHeight(15)
        layout.addWidget(self.profileProgressBar)
        
        group.setLayout(layout)
        return group

    def create_emergency_section(self):
        group = QGroupBox("Emergency")
        group.setMaximumHeight(100)
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.panicButton = QPushButton("PANIC")
        self.panicButton.setFixedSize(80, 40)
        self.panicButton.setStyleSheet("""
            QPushButton {
                background-color: red; 
                color: white; 
                font-weight: bold; 
                font-size: 12px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: darkred;
            }
        """)
        self.panicButton.clicked.connect(self.trigger_panic)
        
        self.clearFailsafeButton = QPushButton("Clear\nFailsafe")
        self.clearFailsafeButton.setFixedSize(60, 40)
        self.clearFailsafeButton.setStyleSheet("""
            QPushButton {
                background-color: orange; 
                font-weight: bold;
                font-size: 10px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: darkorange;
            }
        """)
        self.clearFailsafeButton.clicked.connect(self.clear_failsafe)
        
        button_layout.addWidget(self.panicButton)
        button_layout.addWidget(self.clearFailsafeButton)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        group.setLayout(layout)
        return group

    def create_right_panel(self):
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Live data display
        data_display_group = QGroupBox("Live Data Values")
        data_display_layout = QFormLayout()
        
        self.plateTempDisplay = QLabel("22.0°C")
        self.plateTempDisplay.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: bold;")
        
        self.rectalTempDisplay = QLabel("37.0°C")
        self.rectalTempDisplay.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: bold;")
        
        self.pidOutputDisplay = QLabel("0.0")
        self.pidOutputDisplay.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: bold;")
        
        self.targetTempDisplay = QLabel("37.0°C")
        self.targetTempDisplay.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: bold;")
        
        self.breathRateDisplay = QLabel("150 BPM")
        self.breathRateDisplay.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: bold;")
        
        self.lastUpdateDisplay = QLabel("Never")
        self.lastUpdateDisplay.setStyleSheet("font-family: monospace; font-size: 10px; color: gray;")
        
        data_display_layout.addRow("Cooling Plate:", self.plateTempDisplay)
        data_display_layout.addRow("Rectal Probe:", self.rectalTempDisplay)
        data_display_layout.addRow("PID Output:", self.pidOutputDisplay)
        data_display_layout.addRow("Target Temp:", self.targetTempDisplay)
        data_display_layout.addRow("Breath Rate:", self.breathRateDisplay)
        data_display_layout.addRow("Last Update:", self.lastUpdateDisplay)
        
        data_display_group.setLayout(data_display_layout)
        right_layout.addWidget(data_display_group)
        
        # Event log
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout()
        
        self.logBox = QTextEdit()
        self.logBox.setReadOnly(True)
        self.logBox.setMaximumHeight(300)
        self.logBox.setFont(QFont("Courier", 9))
        
        # Log controls
        log_controls = QHBoxLayout()
        self.clearLogButton = QPushButton("Clear Log")
        self.clearLogButton.clicked.connect(lambda: self.logBox.clear())
        self.clearLogButton.setMaximumWidth(80)
        
        self.autoScrollCheckbox = QCheckBox("Auto-scroll")
        self.autoScrollCheckbox.setChecked(True)
        
        log_controls.addWidget(self.clearLogButton)
        log_controls.addWidget(self.autoScrollCheckbox)
        log_controls.addStretch()
        
        log_layout.addLayout(log_controls)
        log_layout.addWidget(self.logBox)
        log_group.setLayout(log_layout)
        
        right_layout.addWidget(log_group)
        right_widget.setLayout(right_layout)
        return right_widget

    def create_graph_panel(self):
        graph_group = QGroupBox("Live Data Monitoring")
        graph_layout = QVBoxLayout()
        
        # Control buttons for graphs
        graph_control_layout = QHBoxLayout()
        
        self.generateTestDataButton = QPushButton("Generate Test Data")
        self.generateTestDataButton.clicked.connect(self.generate_test_data)
        self.generateTestDataButton.setFixedHeight(30)
        self.generateTestDataButton.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        
        self.clearGraphsButton = QPushButton("Clear Graphs")
        self.clearGraphsButton.clicked.connect(self.clear_graphs)
        self.clearGraphsButton.setFixedHeight(30)
        self.clearGraphsButton.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
        
        self.testBasicPlotButton = QPushButton("Test Basic Plot")
        self.testBasicPlotButton.clicked.connect(self.test_basic_plot)
        self.testBasicPlotButton.setFixedHeight(30)
        self.testBasicPlotButton.setStyleSheet("QPushButton { background-color: #E91E63; color: white; }")
        
        graph_control_layout.addWidget(self.generateTestDataButton)
        graph_control_layout.addWidget(self.clearGraphsButton)
        graph_control_layout.addWidget(self.testBasicPlotButton)
        graph_control_layout.addStretch()
        
        # Create graph widgets with visible pens
        self.tempGraphWidget = pg.PlotWidget(title="Temperatures (°C)")
        self.tempGraphWidget.addLegend()
        self.tempGraphWidget.setLabel('bottom', 'Time (seconds)')
        self.tempGraphWidget.setLabel('left', 'Temperature (°C)')
        self.tempGraphWidget.showGrid(x=True, y=True, alpha=0.3)
        self.tempGraphWidget.setYRange(10, 45)
        self.tempGraphWidget.setXRange(0, 60)
        self.tempGraphWidget.setBackground('w')
        
        # Temperature plots with thick, visible lines
        print("Creating temperature plots...")
        self.temp_plot_plate = self.tempGraphWidget.plot(
            pen=pg.mkPen(color='r', width=4), 
            name="Cooling Plate",
            symbol='o', symbolSize=5, symbolBrush='r'
        )
        
        self.temp_plot_rectal = self.tempGraphWidget.plot(
            pen=pg.mkPen(color='g', width=4), 
            name="Rectal Probe",
            symbol='s', symbolSize=5, symbolBrush='g'
        )
        
        self.temp_plot_target = self.tempGraphWidget.plot(
            pen=pg.mkPen(color='b', width=3, style=Qt.DashLine), 
            name="Target"
        )
        
        self.pidGraphWidget = pg.PlotWidget(title="PID Output")
        self.pidGraphWidget.addLegend()
        self.pidGraphWidget.setLabel('bottom', 'Time (seconds)')
        self.pidGraphWidget.setLabel('left', 'PID Output')
        self.pidGraphWidget.showGrid(x=True, y=True, alpha=0.3)
        self.pidGraphWidget.setYRange(-100, 100)
        self.pidGraphWidget.setXRange(0, 60)
        self.pidGraphWidget.setBackground('w')
        
        self.pid_plot = self.pidGraphWidget.plot(
            pen=pg.mkPen(color='purple', width=4), 
            name="PID Output",
            symbol='t', symbolSize=5, symbolBrush='purple'
        )
        
        self.breathGraphWidget = pg.PlotWidget(title="Breath Frequency (BPM)")
        self.breathGraphWidget.addLegend()
        self.breathGraphWidget.setLabel('bottom', 'Time (seconds)')
        self.breathGraphWidget.setLabel('left', 'Breaths per Minute')
        self.breathGraphWidget.showGrid(x=True, y=True, alpha=0.3)
        self.breathGraphWidget.setYRange(0, 160)
        self.breathGraphWidget.setXRange(0, 60)
        self.breathGraphWidget.setBackground('w')
        
        self.breath_plot = self.breathGraphWidget.plot(
            pen=pg.mkPen(color='orange', width=4), 
            name="Breath Rate",
            symbol='d', symbolSize=5, symbolBrush='orange'
        )
        
        # Set minimum heights for graphs
        self.tempGraphWidget.setMinimumHeight(200)
        self.pidGraphWidget.setMinimumHeight(200)
        self.breathGraphWidget.setMinimumHeight(200)
        
        # Add graphs to layout
        graph_layout.addLayout(graph_control_layout)
        graph_layout.addWidget(self.tempGraphWidget)
        graph_layout.addWidget(self.pidGraphWidget)
        graph_layout.addWidget(self.breathGraphWidget)
        
        graph_group.setLayout(graph_layout)
        return graph_group

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
            
            # Update PID graph
            self.pid_plot.setData(self.graph_data["time"], self.graph_data["pid_output"])
            
            # Update breath graph
            self.breath_plot.setData(self.graph_data["time"], self.graph_data["breath_rate"])
            
            # Auto-scale X axis to show last 60 seconds
            if len(self.graph_data["time"]) > 60:
                x_min = self.graph_data["time"][-60]
                x_max = self.graph_data["time"][-1]
                self.tempGraphWidget.setXRange(x_min, x_max + 5)
                self.pidGraphWidget.setXRange(x_min, x_max + 5)
                self.breathGraphWidget.setXRange(x_min, x_max + 5)
            
        except Exception as e:
            print(f"❌ Update graphs error: {e}")

    def send_and_log_cmd(self, action, state):
        """Send command and log it"""
        if not self.serial_manager.is_connected():
            self.log("❌ Not connected - cannot send command", "error")
            return
            
        self.serial_manager.sendCMD(action, state)
        self.event_logger.log_event(f"CMD: {action} → {state}")
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
                    self.failsafeLabel.setText("ACTIVE")
                    self.failsafeLabel.setStyleSheet("color: red; font-weight: bold;")
                else:
                    self.failsafeLabel.setText("Clear")
                    self.failsafeLabel.setStyleSheet("color: green; font-weight: bold;")

            if "profile_active" in data:
                active = data["profile_active"]
                if active:
                    self.profileStatusLabel.setText("Running")
                    self.profileStatusLabel.setStyleSheet("color: green; font-weight: bold;")
                else:
                    self.profileStatusLabel.setText("Inactive")
                    self.profileStatusLabel.setStyleSheet("color: gray;")

            if "autotune_active" in data:
                is_active = data["autotune_active"]
                self.abortAutotuneButton.setVisible(is_active)
                if is_active:
                    self.autotuneStatusLabel.setText("Running")
                    self.autotuneStatusLabel.setStyleSheet("color: orange; font-weight: bold;")
                else:
                    self.autotuneStatusLabel.setText("Idle")
                    self.autotuneStatusLabel.setStyleSheet("color: gray;")

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

    def start_autotune(self):
        """Start PID autotune"""
        if not self.serial_manager.is_connected():
            self.log("❌ Not connected", "error")
            return
            
        self.send_and_log_cmd("pid", "autotune")
        self.log("🔧 Starting PID autotune...", "command")

    def abort_autotune(self):
        """Abort PID autotune"""
        self.send_and_log_cmd("pid", "abort_autotune")
        self.abortAutotuneButton.setVisible(False)
        self.log("⏹ Autotune aborted", "warning")

    def set_max_output_limit(self):
        """Set maximum PID output limit"""
        value, ok = QInputDialog.getDouble(
            self, "Set Max Output Limit", 
            "Enter max output % (0–100):", 
            20.0, 0.0, 100.0, 1
        )
        if ok:
            self.serial_manager.sendSET("pid_max_output", value)
            self.event_logger.log_event(f"SET: pid_max_output → {value:.1f}%")
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
            
            self.event_logger.log_event(f"SET: PID → Kp={kp}, Ki={ki}, Kd={kd}")
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
            self.event_logger.log_event(f"SET: target_temp → {value:.2f} °C")
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
        QMessageBox.critical(self, "PANIC", "🚨 PANIC triggered! Manual intervention required.")

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
            self.connectionStatusLabel.setStyleSheet("color: red; font-weight: bold; font-size: 11px;")
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
                self.connectionStatusLabel.setStyleSheet("color: green; font-weight: bold; font-size: 11px;")
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