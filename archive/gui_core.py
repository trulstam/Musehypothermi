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
    QToolButton, QFrame
)
from PySide6.QtCore import QTimer, Qt, Slot, QSettings
from PySide6.QtGui import QFont, QPalette, QColor
import pyqtgraph as pg
from framework.serial_comm import SerialManager
from framework.event_logger import EventLogger
from framework.profile_loader import ProfileLoader

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Musehypothermi GUI - Status Monitor v2.0")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        # Initialize UI first
        self.init_ui()

        # Restore persisted UI state
        self.settings = QSettings("Musehypothermi", "MainWindow")
        self.restore_splitter_states()

        # Initialize managers after UI
        self.serial_manager = SerialManager()
        self.serial_manager.data_received.connect(self.process_incoming_data)

        self.event_logger = EventLogger("gui_events")
        self.profile_loader = ProfileLoader(event_logger=self.event_logger)

        # Status request timer
        self.status_request_timer = QTimer()
        self.status_request_timer.timeout.connect(self.request_status)
        self.status_request_timer.start(3000)

        # Data storage
        self.profile_data = []
        self.profile_steps = []
        self.profile_ready = False
        self.profile_upload_pending = False
        self.last_data_time = time.time()

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
        self.main_splitter = QSplitter(Qt.Horizontal)

        # Left panel
        left_widget = self.create_left_panel()
        left_widget.setMinimumWidth(500)
        self.main_splitter.addWidget(left_widget)

        # Right panel
        right_widget = self.create_right_panel()
        right_widget.setMinimumWidth(350)
        self.main_splitter.addWidget(right_widget)

        # Set splitter proportions
        self.main_splitter.setSizes([700, 450])

        # Graph panel
        graph_widget = self.create_graph_panel()

        # Vertical splitter between controls/logs and graphs
        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.vertical_splitter.addWidget(self.main_splitter)
        self.vertical_splitter.addWidget(graph_widget)
        self.vertical_splitter.setChildrenCollapsible(False)
        self.vertical_splitter.setStretchFactor(0, 3)
        self.vertical_splitter.setStretchFactor(1, 2)
        self.vertical_splitter.setSizes([650, 350])

        # Main container
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.vertical_splitter)
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

        # Calibration Group
        calibration_group = QGroupBox("Calibration")
        calibration_layout = QFormLayout()

        # Live raw + calibrated temps (4 desimaler)
        self.calPlateRawLabel = QLabel("Plate raw: n/a")
        self.calPlateCalLabel = QLabel("Plate cal: n/a")
        self.calRectalRawLabel = QLabel("Rectal raw: n/a")
        self.calRectalCalLabel = QLabel("Rectal cal: n/a")

        calibration_layout.addRow("Plate raw:", self.calPlateRawLabel)
        calibration_layout.addRow("Plate calibrated:", self.calPlateCalLabel)
        calibration_layout.addRow("Rectal raw:", self.calRectalRawLabel)
        calibration_layout.addRow("Rectal calibrated:", self.calRectalCalLabel)

        self.calSensorSelector = QComboBox()
        self.calSensorSelector.addItems(["plate", "rectal", "both"])

        self.calReferenceInput = QLineEdit()
        self.calReferenceInput.setPlaceholderText("Reference °C")

        self.calOperatorInput = QLineEdit()
        self.calOperatorInput.setPlaceholderText("Operator name")

        self.addCalPointButton = QPushButton("Add Calibration Point")
        self.commitCalButton = QPushButton("Commit Calibration")

        self.addCalPointButton.clicked.connect(self.add_calibration_point)
        self.commitCalButton.clicked.connect(self.commit_calibration)

        calibration_layout.addRow("Sensor:", self.calSensorSelector)
        calibration_layout.addRow("Reference:", self.calReferenceInput)
        calibration_layout.addRow("Operator:", self.calOperatorInput)
        calibration_layout.addRow(self.addCalPointButton, self.commitCalButton)

        calibration_group.setLayout(calibration_layout)
        layout.addWidget(calibration_group)

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

        # Collapsible graph control toolbar
        toggle_layout = QHBoxLayout()
        toggle_layout.setContentsMargins(0, 0, 0, 0)

        self.graphControlsToggle = QToolButton()
        self.graphControlsToggle.setText("Graph Controls")
        self.graphControlsToggle.setCheckable(True)
        self.graphControlsToggle.setChecked(False)
        self.graphControlsToggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.graphControlsToggle.setArrowType(Qt.RightArrow)
        self.graphControlsToggle.toggled.connect(self.toggle_graph_controls)

        toggle_layout.addWidget(self.graphControlsToggle, alignment=Qt.AlignLeft)
        toggle_layout.addStretch()

        self.graph_controls_container = QFrame()
        self.graph_controls_container.setFrameShape(QFrame.StyledPanel)
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(6)
        controls_layout.setContentsMargins(8, 8, 8, 8)

        self.generateTestDataButton = QPushButton("Generate Test Data")
        self.generateTestDataButton.clicked.connect(self.generate_test_data)
        self.generateTestDataButton.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")

        self.clearGraphsButton = QPushButton("Clear Graphs")
        self.clearGraphsButton.clicked.connect(self.clear_graphs)
        self.clearGraphsButton.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")

        self.autoScaleButton = QPushButton("Auto Scale")
        self.autoScaleButton.clicked.connect(self.auto_scale_graphs)

        self.resetScaleButton = QPushButton("Reset Scale")
        self.resetScaleButton.clicked.connect(self.reset_graph_scales)

        self.testBasicPlotButton = QPushButton("Test Basic Plot")
        self.testBasicPlotButton.clicked.connect(self.test_basic_plot)
        self.testBasicPlotButton.setStyleSheet("QPushButton { background-color: #E91E63; color: white; }")

        for button in (
            self.generateTestDataButton,
            self.clearGraphsButton,
            self.autoScaleButton,
            self.resetScaleButton,
            self.testBasicPlotButton,
        ):
            button.setMinimumHeight(30)
            button.setCursor(Qt.PointingHandCursor)
            controls_layout.addWidget(button)

        controls_layout.addStretch()
        self.graph_controls_container.setLayout(controls_layout)

        graph_layout.addLayout(toggle_layout)
        graph_layout.addWidget(self.graph_controls_container)
        self.graph_controls_container.setVisible(False)

        # Create graph widgets with explicit pen configuration
        self.tempGraphWidget = pg.PlotWidget(title="Temperatures (°C)")
        self.tempGraphWidget.addLegend()
        self.tempGraphWidget.setLabel('bottom', 'Time (seconds)')
        self.tempGraphWidget.setLabel('left', 'Temperature (°C)')
        self.tempGraphWidget.showGrid(x=True, y=True, alpha=0.3)
        self.tempGraphWidget.setYRange(10, 45)
        self.tempGraphWidget.setXRange(0, 60)
        self.tempGraphWidget.setBackground('w')

        self.temp_plot_plate = self.tempGraphWidget.plot(
            pen={'color': (255, 107, 107), 'width': 3},
            name="Cooling Plate",
            symbol='o', symbolSize=4, symbolBrush='r'
        )

        self.temp_plot_rectal = self.tempGraphWidget.plot(
            pen={'color': (78, 205, 196), 'width': 3},
            name="Rectal Probe",
            symbol='s', symbolSize=4, symbolBrush='g'
        )

        self.temp_plot_target = self.tempGraphWidget.plot(
            pen={'color': (69, 183, 209), 'width': 2, 'style': Qt.DashLine},
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
            pen={'color': (155, 89, 182), 'width': 3},
            name="PID Output",
            symbol='t', symbolSize=4, symbolBrush='purple'
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
            pen={'color': (243, 156, 18), 'width': 3},
            name="Breath Rate",
            symbol='d', symbolSize=4, symbolBrush='orange'
        )

        # Add graphs to layout
        graph_layout.addWidget(self.tempGraphWidget)
        graph_layout.addWidget(self.pidGraphWidget)
        graph_layout.addWidget(self.breathGraphWidget)

        graph_group.setLayout(graph_layout)
        return graph_group

    def toggle_graph_controls(self, checked):
        """Show or hide the graph control panel"""
        self.graph_controls_container.setVisible(checked)
        self.graphControlsToggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

    def restore_splitter_states(self):
        """Restore splitter sizes from previous session if available"""
        try:
            vertical_sizes = self.settings.value("splitters/vertical", type=list)
            if vertical_sizes:
                if isinstance(vertical_sizes, str):
                    vertical_sizes = json.loads(vertical_sizes)
                self.vertical_splitter.setSizes([int(size) for size in vertical_sizes])

            horizontal_sizes = self.settings.value("splitters/horizontal", type=list)
            if horizontal_sizes:
                if isinstance(horizontal_sizes, str):
                    horizontal_sizes = json.loads(horizontal_sizes)
                self.main_splitter.setSizes([int(size) for size in horizontal_sizes])
        except Exception:
            # Ignore restoration errors to avoid impacting startup
            pass

    def test_basic_plot(self):
        """Test absolute basic plotting to isolate the problem"""
        try:
            self.log("🧪 Testing basic plot functionality...", "info")

            x_data = [0, 1, 2, 3, 4, 5]
            y_data = [20, 25, 30, 35, 40, 45]

            # Clear all existing data first
            for plot_item in (
                self.temp_plot_plate,
                self.temp_plot_rectal,
                self.temp_plot_target,
                self.pid_plot,
                self.breath_plot,
            ):
                plot_item.clear()

            self.log("✅ Cleared existing plot data", "success")

            # Test plot with explicit red pen
            self.temp_plot_plate.setData(
                x_data,
                y_data,
                pen='r',
                symbol='o',
                symbolBrush='r'
            )

            # Force graph to show the data range
            self.tempGraphWidget.setXRange(0, 6)
            self.tempGraphWidget.setYRange(15, 50)

            # Force update and repaint
            self.tempGraphWidget.getPlotItem().getViewBox().updateAutoRange()
            self.tempGraphWidget.update()
            self.tempGraphWidget.repaint()

            # Test if we can get the data back
            plot_data = self.temp_plot_plate.getData()
            if plot_data is not None:
                x_back, y_back = plot_data
                self.log(
                    f"Retrieved data points: x={list(x_back)}, y={list(y_back)}",
                    "info",
                )
            else:
                self.log("❌ No data retrieved from plot", "error")

            # Check plot item properties
            plot_item = self.tempGraphWidget.getPlotItem()
            data_items = plot_item.listDataItems()
            self.log(f"Plot has {len(data_items)} data items", "info")
            for index, item in enumerate(data_items):
                self.log(f"  Item {index}: {type(item).__name__}", "info")

            self.log("✅ Basic plot test complete - check log for details", "success")

        except Exception as e:
            self.log(f"❌ Error in basic plot test: {e}", "error")
            import traceback
            traceback.print_exc()

    def send_and_log_cmd(self, action, state):
        """Send command with proper error handling and logging"""
        try:
            if not self.serial_manager.is_connected():
                self.log("❌ Cannot send command - not connected", "error")
                return False
                
            self.serial_manager.sendCMD(action, state)
            self.event_logger.log_event(f"CMD: {action} → {state}")
            self.log(f"🛰️ Sent CMD: {action} = {state}")
            return True
        except Exception as e:
            self.log(f"❌ Error sending command: {e}", "error")
            return False

    def fetch_pid_parameters(self):
        """Fetch PID parameters from Arduino with better feedback"""
        if not self.serial_manager.is_connected():
            self.log("❌ Not connected - cannot fetch parameters", "error")
            return
            
        self.serial_manager.sendCMD("get", "pid_params")
        self.log("🔄 Fetching PID parameters from Arduino...")
        
        # Also request status to get max output and other values
        QTimer.singleShot(200, lambda: self.serial_manager.sendCMD("get", "status"))
        QTimer.singleShot(400, lambda: self.serial_manager.sendCMD("get", "config"))

    def start_autotune(self):
        """Start autotune with proper state management"""
        if self.send_and_log_cmd("pid", "autotune"):
            self.autotune_in_progress = True
            self.autotuneButton.setVisible(False)
            self.abortAutotuneButton.setVisible(True)
            self.autotuneStatusLabel.setText("Running…")
            self.log("🔄 Autotune starting...")

    def abort_autotune(self):
        """Abort autotune with proper state management"""
        if self.send_and_log_cmd("pid", "abort_autotune"):
            self.log("⛔ Autotune abort requested...")

    def set_max_output_limit(self):
        """Set maximum PID output with validation and better feedback"""
        try:
            current_value = 20.0
            try:
                current_text = self.maxOutputLabel.text()
                if "%" in current_text:
                    current_value = float(current_text.replace("%", ""))
            except:
                pass
                
            value, ok = QInputDialog.getDouble(
                self, "Set Max Output Limit", 
                "Enter max output % (0–100):", 
                current_value, 0.0, 100.0, 1
            )
            if ok:
                self.serial_manager.sendSET("pid_max_output", value)
                self.event_logger.log_event(f"SET: pid_max_output → {value:.1f}%")
                self.log(f"⚙️ Max output limit set to {value:.1f}%")
                
                # Force status update after setting
                QTimer.singleShot(500, self.request_status)
                
                # Also update the display immediately (optimistic update)
                self.maxOutputLabel.setText(f"{value:.1f}%")
                
        except Exception as e:
            self.log(f"❌ Error setting max output: {e}", "error")

    def log(self, message, level="info"):
        """Enhanced logging with levels and timestamps"""
        try:
            if not hasattr(self, 'logBox'):
                print(f"LOG (pre-UI): {message}")
                return
                
            timestamp = time.strftime("%H:%M:%S")
            
            colors = {
                "error": "red",
                "warning": "orange", 
                "success": "green",
                "info": "black"
            }
            
            color = colors.get(level, "black")
            formatted_message = f'<span style="color: {color}">[{timestamp}] {message}</span>'
            
            self.logBox.append(formatted_message)
            
            if hasattr(self, 'autoScrollCheckbox') and self.autoScrollCheckbox.isChecked():
                scrollbar = self.logBox.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
        except Exception as e:
            print(f"LOG ERROR: {e} - Original message: {message}")
        
        print(f"LOG: {message}")

    @Slot(dict)
    def process_incoming_data(self, data):
        """Enhanced data processing - ONLY UPDATE GRAPHS FROM ARDUINO DATA"""
        if not data:
            return

        try:
            # Update live data display first
            self.update_live_data_display(data)

            # Oppdater kalibreringsvisning – rå og kalibrerte verdier
            plate_raw = data.get("cooling_plate_temp_raw")
            plate_cal = data.get("cooling_plate_temp")
            rectal_raw = data.get("anal_probe_temp_raw")
            rectal_cal = data.get("anal_probe_temp")

            def fmt_temp(value):
                if value is None:
                    return "n/a"
                try:
                    return f"{float(value):.4f} °C"
                except (TypeError, ValueError):
                    return "n/a"

            self.calPlateRawLabel.setText(fmt_temp(plate_raw))
            self.calPlateCalLabel.setText(fmt_temp(plate_cal))
            self.calRectalRawLabel.setText(fmt_temp(rectal_raw))
            self.calRectalCalLabel.setText(fmt_temp(rectal_cal))

            # Update PID parameters
            if all(key in data for key in ["pid_kp", "pid_ki", "pid_kd"]):
                kp, ki, kd = data["pid_kp"], data["pid_ki"], data["pid_kd"]
                self.kpInput.setText(str(kp))
                self.kiInput.setText(str(ki))
                self.kdInput.setText(str(kd))
                self.pidParamsLabel.setText(f"Kp: {kp}, Ki: {ki}, Kd: {kd}")

            # NEW: Handle autotune results specifically
            if "autotune_results" in data:
                results = data["autotune_results"]
                if all(key in results for key in ["kp", "ki", "kd"]):
                    new_kp = results["kp"]
                    new_ki = results["ki"] 
                    new_kd = results["kd"]
                    
                    # Update input fields with new values
                    self.kpInput.setText(f"{new_kp:.3f}")
                    self.kiInput.setText(f"{new_ki:.3f}")
                    self.kdInput.setText(f"{new_kd:.3f}")
                    self.pidParamsLabel.setText(f"Kp: {new_kp:.3f}, Ki: {new_ki:.3f}, Kd: {new_kd:.3f}")
                    
                    # Show success message with results
                    QMessageBox.information(
                        self, 
                        "Autotune Complete",
                        f"New PID parameters calculated:\n\n"
                        f"Kp: {new_kp:.3f}\n"
                        f"Ki: {new_ki:.3f}\n"
                        f"Kd: {new_kd:.3f}\n\n"
                        f"Parameters have been automatically loaded.\n"
                        f"Click 'Set' to apply them, then 'Save' to store in EEPROM."
                    )
                    
                    self.log(f"✅ Autotune complete - New PID: Kp={new_kp:.3f}, Ki={new_ki:.3f}, Kd={new_kd:.3f}", "success")

            # Update status labels
            self.process_status_only(data)

            # UPDATE GRAPHS ONLY FROM ARDUINO DATA
            temp_keys = ["cooling_plate_temp", "anal_probe_temp", "pid_output", "breath_freq_bpm", "plate_target_active"]
            has_temp_data = any(key in data for key in temp_keys)
            
            if has_temp_data:
                self.graph_mode = "live"
                self.update_graph_data_from_arduino(data)

            # Handle events
            if "event" in data:
                event_msg = data["event"]
                self.log(f"📢 EVENT: {event_msg}")
                self.event_logger.log_event(event_msg)

            # Handle responses
            if "response" in data:
                response_msg = data["response"]
                self.log(f"📥 RESPONSE: {response_msg}")

                if isinstance(response_msg, str):
                    response_lower = response_msg.lower()

                    if self.profile_upload_pending and response_lower.startswith("profile"):
                        self.profile_upload_pending = False

                        if response_lower == "profile loaded":
                            self.profile_ready = True
                            self._update_profile_button_states()
                            success_message = "Profile upload confirmed by controller"
                            self.log(f"✅ {success_message}", "success")
                            self.event_logger.log_event(success_message)
                        else:
                            self.profile_ready = False
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
                        self._update_profile_button_states()
                        failure_message = f"Profile upload failed: {response_msg}"
                        self.log(f"❌ {failure_message}", "error")
                        self.event_logger.log_event(failure_message)
                        QMessageBox.warning(self, "Profile Upload Failed", response_msg)

            self.last_data_time = time.time()

        except Exception as e:
            self.log(f"❌ Error processing incoming data: {e}", "error")
            print(f"Process data error: {e}")

    def update_graph_data_from_arduino(self, data):
        """Update graph data ONLY from Arduino - with EXTENSIVE DEBUGGING"""
        try:
            # Use simple incrementing time instead of timestamps
            if not hasattr(self, 'data_point_counter'):
                self.data_point_counter = 0
                self.log("🕐 Started Arduino data with simple counter timing", "info")
                self.graph_data = {
                    "time": [],
                    "plate_temp": [],
                    "rectal_temp": [],
                    "pid_output": [],
                    "breath_rate": [],
                    "target_temp": []
                }
            
            # Simple incremental time (1 second per data point)
            self.data_point_counter += 1
            simple_time = float(self.data_point_counter)
            self.graph_data["time"].append(simple_time)

            # Extract data with defaults
            plate_temp = float(data.get("cooling_plate_temp", 22.0))
            rectal_temp = float(data.get("anal_probe_temp", 37.0))
            pid_output = float(data.get("pid_output", 0.0))
            breath_rate = float(data.get("breath_freq_bpm", 150.0))
            target_temp = float(data.get("plate_target_active", 37.0))

            self.graph_data["plate_temp"].append(plate_temp)
            self.graph_data["rectal_temp"].append(rectal_temp)
            self.graph_data["pid_output"].append(pid_output)
            self.graph_data["breath_rate"].append(breath_rate)
            self.graph_data["target_temp"].append(target_temp)

            # EXTENSIVE DEBUG for first few points
            if self.data_point_counter <= 5:
                print("=" * 60)
                print(f"ARDUINO DATA DEBUG - Point #{self.data_point_counter}")
                print(f"Raw data keys: {list(data.keys())}")
                print(f"Extracted values:")
                print(f"  time: {simple_time}s")
                print(f"  plate_temp: {plate_temp}°C")
                print(f"  rectal_temp: {rectal_temp}°C")
                print(f"  pid_output: {pid_output}")
                print(f"  breath_rate: {breath_rate} BPM")
                print(f"  target_temp: {target_temp}°C")
                print(f"Graph data lengths:")
                print(f"  time: {len(self.graph_data['time'])}")
                print(f"  plate_temp: {len(self.graph_data['plate_temp'])}")
                print(f"  rectal_temp: {len(self.graph_data['rectal_temp'])}")
                print("=" * 60)

            # Trim data to last 200 points for performance
            max_points = 200
            if len(self.graph_data["time"]) > max_points:
                for key in self.graph_data:
                    self.graph_data[key] = self.graph_data[key][-max_points:]
                self.data_point_counter = max_points

            # Update plots with EXTENSIVE DEBUG
            if self.data_point_counter <= 3:
                print(f"UPDATING PLOTS - Point #{self.data_point_counter}")
                print(f"Time range: {self.graph_data['time'][0]} to {self.graph_data['time'][-1]}")
                print(f"Plate temp range: {min(self.graph_data['plate_temp'])} to {max(self.graph_data['plate_temp'])}")
            
            try:
                self.temp_plot_plate.setData(self.graph_data["time"], self.graph_data["plate_temp"])
                if self.data_point_counter <= 3:
                    print("✅ temp_plot_plate.setData() - SUCCESS")
            except Exception as e:
                print(f"❌ temp_plot_plate.setData() - ERROR: {e}")
                
            try:
                self.temp_plot_rectal.setData(self.graph_data["time"], self.graph_data["rectal_temp"])
                if self.data_point_counter <= 3:
                    print("✅ temp_plot_rectal.setData() - SUCCESS")
            except Exception as e:
                print(f"❌ temp_plot_rectal.setData() - ERROR: {e}")
                
            try:
                self.temp_plot_target.setData(self.graph_data["time"], self.graph_data["target_temp"])
                if self.data_point_counter <= 3:
                    print("✅ temp_plot_target.setData() - SUCCESS")
            except Exception as e:
                print(f"❌ temp_plot_target.setData() - ERROR: {e}")
                
            try:
                self.pid_plot.setData(self.graph_data["time"], self.graph_data["pid_output"])
                if self.data_point_counter <= 3:
                    print("✅ pid_plot.setData() - SUCCESS")
            except Exception as e:
                print(f"❌ pid_plot.setData() - ERROR: {e}")
                
            try:
                self.breath_plot.setData(self.graph_data["time"], self.graph_data["breath_rate"])
                if self.data_point_counter <= 3:
                    print("✅ breath_plot.setData() - SUCCESS")
            except Exception as e:
                print(f"❌ breath_plot.setData() - ERROR: {e}")

            # Auto-adjust X-axis to show scrolling window of last 60 seconds
            if len(self.graph_data["time"]) > 1:
                latest_time = self.graph_data["time"][-1]
                start_time = max(0, latest_time - 60)
                
                if self.data_point_counter <= 3:
                    print(f"Setting X-range: {start_time} to {latest_time + 2}")
                
                try:
                    for widget in [self.tempGraphWidget, self.pidGraphWidget, self.breathGraphWidget]:
                        widget.setXRange(start_time, latest_time + 2)
                    if self.data_point_counter <= 3:
                        print("✅ X-range setting - SUCCESS")
                except Exception as e:
                    print(f"❌ X-range setting - ERROR: {e}")

        except Exception as e:
            self.log(f"❌ Error updating graphs from Arduino: {e}", "error")
            print(f"Arduino graph update error: {e}")
            import traceback
            traceback.print_exc()

    def process_status_only(self, data):
        """Process only status updates, not graph data"""
        try:
            # Update status labels
            if "failsafe_active" in data:
                is_active = data["failsafe_active"]
                if is_active:
                    reason = data.get("failsafe_reason", "Unknown")
                    self.failsafeLabel.setText(f"ACTIVE: {reason}")
                    self.failsafeLabel.setStyleSheet("color: red; font-weight: bold;")
                else:
                    self.failsafeLabel.setText("Inactive")
                    self.failsafeLabel.setStyleSheet("color: green; font-weight: bold;")

            # Update autotune status
            if "autotune_active" in data:
                was_active = getattr(self, "autotune_in_progress", False)
                is_active = bool(data["autotune_active"])
                self.autotune_in_progress = is_active

                if is_active:
                    self.autotuneButton.setVisible(False)
                    self.abortAutotuneButton.setVisible(True)
                    progress = data.get("autotune_progress")
                    phase = data.get("autotune_phase", "running")
                    label = "Running…"
                    if progress is not None:
                        label += f" ({int(progress)}%)"
                    label += f" [{phase}]"
                    self.autotuneStatusLabel.setText(label)
                else:
                    self.autotuneButton.setVisible(True)
                    self.abortAutotuneButton.setVisible(False)

                    status = str(data.get("autotune_status", "idle"))

                    if was_active:
                        if status.lower() == "aborted":
                            self.autotuneStatusLabel.setText("Aborted")
                        else:
                            self.autotuneStatusLabel.setText("Completed")
                            self.event_logger.log_event("AUTOTUNE_COMPLETED")
                            self.log("✅ Autotune completed", "success")

                            if all(key in data for key in ["pid_kp", "pid_ki", "pid_kd"]):
                                kp, ki, kd = data["pid_kp"], data["pid_ki"], data["pid_kd"]
                                self.kpInput.setText(f"{kp:.3f}")
                                self.kiInput.setText(f"{ki:.3f}")
                                self.kdInput.setText(f"{kd:.3f}")
                                self.pidParamsLabel.setText(f"Kp: {kp:.3f}, Ki: {ki:.3f}, Kd: {kd:.3f}")
                    else:
                        self.autotuneStatusLabel.setText(status.title())

            # Update profile status
            if "profile_active" in data:
                is_active = data["profile_active"]
                self.profile_active = is_active
                
                if is_active:
                    paused = data.get("profile_paused", False)
                    step = data.get("profile_step", 0)
                    if paused:
                        self.profileStatusLabel.setText(f"Paused (Step {step})")
                    else:
                        self.profileStatusLabel.setText(f"Active (Step {step})")
                else:
                    self.profileStatusLabel.setText("Inactive")

            # Update max output
            if "pid_max_output" in data:
                max_output = data["pid_max_output"]
                self.maxOutputLabel.setText(f"{max_output:.1f}%")

        except Exception as e:
            self.log(f"❌ Error processing status data: {e}", "error")

    def update_live_data_display(self, data):
        """Update the live data display fields"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            
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
            
            self.lastUpdateDisplay.setText(timestamp)
            
        except Exception as e:
            print(f"Error updating live display: {e}")

    def request_status(self):
        """Request status update from Arduino"""
        if self.serial_manager.is_connected():
            self.serial_manager.sendCMD("get", "status")

    def initial_sync(self):
        """Perform initial synchronization after connection"""
        if self.serial_manager.is_connected():
            self.log("🔄 Performing initial sync...")
            self.serial_manager.sendCMD("get", "pid_params")
            QTimer.singleShot(200, lambda: self.serial_manager.sendCMD("get", "config"))
            QTimer.singleShot(400, self.request_status)

    def trigger_panic(self):
        """Trigger emergency panic with confirmation"""
        reply = QMessageBox.question(
            self, "EMERGENCY PANIC", 
            "Are you sure you want to trigger emergency panic?\n\nThis will immediately stop all operations!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.serial_manager.sendCMD("panic", "")
            self.event_logger.log_event("CMD: panic triggered")
            self.log("🚨 PANIC TRIGGERED!", "error")
            QMessageBox.critical(self, "PANIC", "🚨 PANIC triggered! Manual intervention required.")

    def clear_failsafe(self):
        """Clear failsafe state"""
        if self.send_and_log_cmd("failsafe_clear", ""):
            self.log("🔧 Failsafe clear requested")

    def save_pid_to_eeprom(self):
        """Save current PID parameters to EEPROM"""
        if self.send_and_log_cmd("save_eeprom", ""):
            self.log("💾 EEPROM save requested", "success")

    def set_pid_values(self):
        """Set PID parameters with validation"""
        try:
            kp = float(self.kpInput.text())
            ki = float(self.kiInput.text())
            kd = float(self.kdInput.text())
            
            # Basic validation
            if not (0 <= kp <= 100):
                raise ValueError("Kp must be between 0 and 100")
            if not (0 <= ki <= 50):
                raise ValueError("Ki must be between 0 and 50")
            if not (0 <= kd <= 50):
                raise ValueError("Kd must be between 0 and 50")
            
            self.serial_manager.sendSET("pid_kp", kp)
            self.serial_manager.sendSET("pid_ki", ki)
            self.serial_manager.sendSET("pid_kd", kd)
            
            self.event_logger.log_event(f"SET: PID → Kp={kp}, Ki={ki}, Kd={kd}")
            self.log(f"✅ PID parameters set: Kp={kp}, Ki={ki}, Kd={kd}", "success")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Error in PID parameters: {e}")
            self.log(f"❌ Invalid PID input: {e}", "error")
        except Exception as e:
            self.log(f"❌ Error setting PID values: {e}", "error")

    def set_manual_setpoint(self):
        """Set manual temperature setpoint with validation"""
        try:
            value = float(self.setpointInput.text())

            # Validation
            if not (-10 <= value <= 50):
                raise ValueError("Temperature must be between -10°C and 50°C")

            self.serial_manager.sendSET("target_temp", value)
            self.event_logger.log_event(f"SET: target_temp → {value:.2f} °C")
            self.log(f"✅ Target temperature SET: {value:.2f} °C", "success")

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Error in temperature: {e}")
            self.log(f"❌ Invalid temperature input: {e}", "error")
        except Exception as e:
            self.log(f"❌ Error setting setpoint: {e}", "error")

    def add_calibration_point(self):
        sensor = self.calSensorSelector.currentText()
        if sensor not in ("plate", "rectal"):
            QMessageBox.warning(self, "Invalid sensor", "Calibration point can only be added for 'plate' or 'rectal'.")
            return
        try:
            reference = float(self.calReferenceInput.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid reference", "Please enter a numeric reference temperature.")
            return

        payload = {"sensor": sensor, "reference": reference}
        self.serial_manager.sendSET("calibration_point", payload)
        msg = f"SET: calibration_point → sensor={sensor}, reference={reference}"
        self.event_logger.log_event(msg)
        self.log(f"📐 {msg}")

    def commit_calibration(self):
        sensor = self.calSensorSelector.currentText()
        operator = self.calOperatorInput.text().strip()
        if not operator:
            operator, ok = QInputDialog.getText(self, "Operator name", "Enter operator name:")
            if not ok or not operator.strip():
                QMessageBox.warning(self, "Missing operator", "Operator name is required to commit calibration.")
                return
            operator = operator.strip()

        timestamp = int(time.time())

        payload = {
            "sensor": sensor,         # "plate", "rectal" eller "both"
            "operator": operator,
            "timestamp": timestamp,
        }
        self.serial_manager.sendSET("calibration_commit", payload)
        msg = f"SET: calibration_commit → sensor={sensor}, operator={operator}, ts={timestamp}"
        self.event_logger.log_event(msg)
        self.log(f"💾 {msg}")

    def _convert_profile_points_to_steps(self, profile_points):
        """Convert loader data into firmware profile steps.

        Mirrors the transformation used by ``profile_graph_popup.ProfileGraphPopup``
        so both UIs validate profiles consistently.
        """
        if not profile_points:
            raise ValueError("Loaded profile is empty")

        first_entry = profile_points[0]
        step_keys = {"plate_start_temp", "plate_end_temp", "total_step_time_ms"}

        if step_keys.issubset(first_entry.keys()):
            steps = []
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

        steps = []

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
        """Enable/disable profile control buttons based on upload status."""
        connected = self.serial_manager.is_connected()
        uploading = self.profile_upload_pending
        ready = self.profile_ready and not uploading and connected

        self.startProfileButton.setEnabled(ready)
        self.pauseProfileButton.setEnabled(ready)
        self.resumeProfileButton.setEnabled(False)
        self.stopProfileButton.setEnabled(False)

    def load_profile(self):
        """Load temperature profile with proper error handling"""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self, "Load Temperature Profile", "",
                "JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
            )
            
            if file_name:
                try:
                    self.profile_data = self.profile_loader.load_profile(file_name)
                except Exception as exc:
                    self.profile_data = []
                    self.profile_steps = []
                    self.profile_ready = False
                    self.profile_upload_pending = False
                    self._update_profile_button_states()
                    error_message = f"Failed to load profile: {exc}"
                    self.log(f"❌ {error_message}", "error")
                    QMessageBox.warning(self, "Load Error", error_message)
                    return

                filename = os.path.basename(file_name)
                self.profileFileLabel.setText(f"Loaded: {filename}")
                self.profileFileLabel.setStyleSheet("color: green; font-weight: bold;")

                try:
                    self.profile_steps = self._convert_profile_points_to_steps(self.profile_data)
                except ValueError as exc:
                    self.profile_steps = []
                    self.profile_ready = False
                    self.profile_upload_pending = False
                    self._update_profile_button_states()
                    error_message = f"Profile conversion error: {exc}"
                    self.log(f"❌ {error_message}", "error")
                    QMessageBox.warning(self, "Profile Error", error_message)
                    return

                if not self.profile_steps:
                    self.profile_ready = False
                    self.profile_upload_pending = False
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
                self._update_profile_button_states()

                self.log(
                    f"✅ Profile loaded: {filename} ({len(self.profile_data)} points)",
                    "success",
                )
                self.event_logger.log_event(
                    f"PROFILE_LOADED file={filename} points={len(self.profile_data)}"
                )

                if self.serial_manager.is_connected():
                    self.serial_manager.sendSET("profile", self.profile_steps)
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
            self.log(f"❌ Error loading profile: {e}", "error")
            QMessageBox.critical(self, "Error", f"An error occurred while loading the profile:\n{e}")

    def refresh_ports(self):
        """Refresh available serial ports"""
        try:
            self.portSelector.clear()
            ports = self.serial_manager.list_ports()
            self.portSelector.addItems(ports)
            if hasattr(self, 'logBox'):
                self.log(f"🔄 Found {len(ports)} serial ports")
        except Exception as e:
            if hasattr(self, 'logBox'):
                self.log(f"❌ Error refreshing ports: {e}", "error")
            else:
                print(f"Error refreshing ports: {e}")

    def toggle_connection(self):
        """Toggle serial connection with proper state management"""
        try:
            if self.serial_manager.is_connected():
                # Disconnect
                self.serial_manager.disconnect()
                self.connectButton.setText("Connect")
                self.connectionStatusLabel.setText("Disconnected")
                self.connectionStatusLabel.setStyleSheet("color: red; font-weight: bold;")
                self.connection_established = False
                
                # Reset timing variables
                if hasattr(self, 'data_point_counter'):
                    delattr(self, 'data_point_counter')
                
                self.graph_mode = "test"
                self.disable_connection_dependent_controls()
                self.log("🔌 Disconnected - timing reset", "warning")
                self.event_logger.log_event("Disconnected")
                
            else:
                # Connect
                port = self.portSelector.currentText()
                if not port:
                    QMessageBox.warning(self, "No Port", "Please select a serial port first.")
                    return
                    
                if self.serial_manager.connect(port):
                    self.connectButton.setText("Disconnect")
                    self.connectionStatusLabel.setText(f"Connected to {port}")
                    self.connectionStatusLabel.setStyleSheet("color: green; font-weight: bold;")
                    self.connection_established = True
                    
                    # Clear graphs and reset timing
                    self.clear_graphs()
                    self.graph_mode = "live"
                    
                    self.enable_connection_dependent_controls()
                    self.log(f"🔌 Connected to {port} - graphs ready for Arduino data", "success")
                    self.event_logger.log_event(f"Connected to {port}")
                    self.sync_timer.start(1000)
                    
                else:
                    QMessageBox.critical(self, "Connection Failed", f"Failed to connect to {port}")
                    self.log(f"❌ Failed to connect to {port}", "error")
                    
        except Exception as e:
            self.log(f"❌ Connection error: {e}", "error")
            QMessageBox.critical(self, "Error", f"Connection error:\n{e}")

    def enable_connection_dependent_controls(self):
        """Enable controls that require active connection"""
        controls = [
            self.startPIDButton, self.stopPIDButton, self.setPIDButton,
            self.setSetpointButton, self.autotuneButton, self.setMaxOutputButton,
            self.saveEEPROMButton, self.panicButton, self.clearFailsafeButton,
            self.fetchPIDButton
        ]
        
        for control in controls:
            control.setEnabled(True)

        self._update_profile_button_states()

    def disable_connection_dependent_controls(self):
        """Disable controls that require active connection"""
        controls = [
            self.startPIDButton, self.stopPIDButton, self.setPIDButton,
            self.setSetpointButton, self.autotuneButton, self.setMaxOutputButton,
            self.saveEEPROMButton, self.panicButton, self.clearFailsafeButton,
            self.startProfileButton, self.pauseProfileButton, 
            self.resumeProfileButton, self.stopProfileButton, self.fetchPIDButton
        ]
        
        for control in controls:
            control.setEnabled(False)

        self.profile_ready = False
        self.profile_upload_pending = False

    def clear_graphs(self):
        """Clear all graph data and reset timing"""
        try:
            print("DEBUG: Clearing graphs and resetting timing...")
            
            # Clear data arrays
            self.graph_data = {
                "time": [],
                "plate_temp": [],
                "rectal_temp": [],
                "pid_output": [],
                "breath_rate": [],
                "target_temp": []
            }
            
            # Reset timing variables
            if hasattr(self, 'data_point_counter'):
                delattr(self, 'data_point_counter')
            self.graph_mode = "test"
            
            # Clear the plots
            self.temp_plot_plate.setData([], [])
            self.temp_plot_rectal.setData([], [])
            self.temp_plot_target.setData([], [])
            self.pid_plot.setData([], [])
            self.breath_plot.setData([], [])
            
            # Reset ranges
            self.tempGraphWidget.setYRange(10, 45)
            self.tempGraphWidget.setXRange(0, 60)
            self.pidGraphWidget.setYRange(-100, 100)
            self.pidGraphWidget.setXRange(0, 60)
            self.breathGraphWidget.setYRange(0, 160)
            self.breathGraphWidget.setXRange(0, 60)
            
            self.log("🧹 Graphs cleared - ready for test data or Arduino data", "info")
            
        except Exception as e:
            self.log(f"❌ Error clearing graphs: {e}", "error")
            print(f"CLEAR ERROR: {e}")

    def generate_test_data(self):
        """Generate test data with proper timing and EXTENSIVE DEBUGGING"""
        try:
            self.log("🧪 Generating test data with debug info...", "info")
            
            # Clear graphs first
            self.clear_graphs()
            self.graph_mode = "test"
            
            # Generate test data with proper time scale
            test_times = [float(i * 2) for i in range(30)]  # 0, 2, 4... 58 seconds
            test_plate = [25.0 + i * 0.3 for i in range(30)]  # Gradual rise
            test_rectal = [37.0 - i * 0.1 for i in range(30)]  # Gradual drop
            test_pid = [10 * (i % 11) for i in range(30)]  # Oscillating
            test_breath = [150.0 - i * 2.0 for i in range(30)]  # Decreasing
            test_target = [30.0 for i in range(30)]  # Constant
            
            # EXTENSIVE DEBUG OUTPUT
            print("=" * 60)
            print("TEST DATA GENERATION DEBUG:")
            print(f"Times length: {len(test_times)}")
            print(f"Times first 5: {test_times[:5]}")
            print(f"Times last 5: {test_times[-5:]}")
            print(f"Plate temps first 5: {test_plate[:5]}")
            print(f"Plate temps last 5: {test_plate[-5:]}")
            print(f"PID values first 5: {test_pid[:5]}")
            print(f"PID range: {min(test_pid)} to {max(test_pid)}")
            print("=" * 60)
            
            # Check if plot objects exist
            print(f"Plot objects exist:")
            print(f"  temp_plot_plate: {hasattr(self, 'temp_plot_plate')}")
            print(f"  temp_plot_rectal: {hasattr(self, 'temp_plot_rectal')}")
            print(f"  temp_plot_target: {hasattr(self, 'temp_plot_target')}")
            print(f"  pid_plot: {hasattr(self, 'pid_plot')}")
            print(f"  breath_plot: {hasattr(self, 'breath_plot')}")
            
            # Update plots directly with DETAILED DEBUG
            print("Setting data on plots...")
            try:
                self.temp_plot_plate.setData(test_times, test_plate)
                print("✅ temp_plot_plate.setData() - SUCCESS")
            except Exception as e:
                print(f"❌ temp_plot_plate.setData() - ERROR: {e}")
                
            try:
                self.temp_plot_rectal.setData(test_times, test_rectal)
                print("✅ temp_plot_rectal.setData() - SUCCESS")
            except Exception as e:
                print(f"❌ temp_plot_rectal.setData() - ERROR: {e}")
                
            try:
                self.temp_plot_target.setData(test_times, test_target)
                print("✅ temp_plot_target.setData() - SUCCESS")
            except Exception as e:
                print(f"❌ temp_plot_target.setData() - ERROR: {e}")
                
            try:
                self.pid_plot.setData(test_times, test_pid)
                print("✅ pid_plot.setData() - SUCCESS")
            except Exception as e:
                print(f"❌ pid_plot.setData() - ERROR: {e}")
                
            try:
                self.breath_plot.setData(test_times, test_breath)
                print("✅ breath_plot.setData() - SUCCESS")
            except Exception as e:
                print(f"❌ breath_plot.setData() - ERROR: {e}")
            
            # Check graph widget ranges
            print("Graph widget ranges:")
            try:
                temp_xrange = self.tempGraphWidget.getViewBox().viewRange()[0]
                temp_yrange = self.tempGraphWidget.getViewBox().viewRange()[1]
                print(f"  Temperature graph X-range: {temp_xrange}")
                print(f"  Temperature graph Y-range: {temp_yrange}")
            except Exception as e:
                print(f"  Temperature graph range ERROR: {e}")
                
            try:
                pid_xrange = self.pidGraphWidget.getViewBox().viewRange()[0]
                pid_yrange = self.pidGraphWidget.getViewBox().viewRange()[1]
                print(f"  PID graph X-range: {pid_xrange}")
                print(f"  PID graph Y-range: {pid_yrange}")
            except Exception as e:
                print(f"  PID graph range ERROR: {e}")
            
            # Set proper X-axis range with debug
            print("Setting X-axis ranges...")
            try:
                self.tempGraphWidget.setXRange(0, 60)
                print("✅ tempGraphWidget.setXRange(0, 60) - SUCCESS")
            except Exception as e:
                print(f"❌ tempGraphWidget.setXRange() - ERROR: {e}")
                
            try:
                self.pidGraphWidget.setXRange(0, 60)
                print("✅ pidGraphWidget.setXRange(0, 60) - SUCCESS")
            except Exception as e:
                print(f"❌ pidGraphWidget.setXRange() - ERROR: {e}")
                
            try:
                self.breathGraphWidget.setXRange(0, 60)
                print("✅ breathGraphWidget.setXRange(0, 60) - SUCCESS")
            except Exception as e:
                print(f"❌ breathGraphWidget.setXRange() - ERROR: {e}")
            
            # Force graph refresh
            print("Forcing graph refresh...")
            try:
                for widget in [self.tempGraphWidget, self.pidGraphWidget, self.breathGraphWidget]:
                    widget.update()
                    widget.repaint()
                print("✅ Graph refresh - SUCCESS")
            except Exception as e:
                print(f"❌ Graph refresh - ERROR: {e}")
            
            # Update live display
            self.update_live_data_display({
                "cooling_plate_temp": test_plate[-1],
                "anal_probe_temp": test_rectal[-1],
                "pid_output": test_pid[-1],
                "breath_freq_bpm": test_breath[-1],
                "plate_target_active": test_target[-1]
            })
            
            print("=" * 60)
            self.log("✅ Test data loaded - check console for detailed debug info", "success")
            
        except Exception as e:
            self.log(f"❌ Error generating test data: {e}", "error")
            print(f"TEST DATA ERROR: {e}")
            import traceback
            traceback.print_exc()

    def auto_scale_graphs(self):
        """Manually triggered auto-scaling"""
        try:
            if len(self.graph_data["time"]) < 5:
                self.log("Not enough data for auto-scaling", "warning")
                return
                
            # Temperature graph auto-scaling
            temp_values = self.graph_data["plate_temp"] + self.graph_data["rectal_temp"] + self.graph_data["target_temp"]
            if temp_values:
                temp_min = min(temp_values) - 2
                temp_max = max(temp_values) + 2
                self.tempGraphWidget.setYRange(temp_min, temp_max, padding=0.05)
            
            # PID output auto-scaling
            if self.graph_data["pid_output"]:
                pid_min = min(self.graph_data["pid_output"]) - 5
                pid_max = max(self.graph_data["pid_output"]) + 5
                self.pidGraphWidget.setYRange(pid_min, pid_max, padding=0.05)
            
            # Breath rate auto-scaling
            if self.graph_data["breath_rate"]:
                breath_min = max(0, min(self.graph_data["breath_rate"]) - 10)
                breath_max = max(self.graph_data["breath_rate"]) + 10
                self.breathGraphWidget.setYRange(breath_min, breath_max, padding=0.05)
                
        except Exception as e:
            self.log(f"❌ Error auto-scaling graphs: {e}", "error")

    def reset_graph_scales(self):
        """Reset graphs to default scale ranges"""
        try:
            # Reset Y ranges
            self.tempGraphWidget.setYRange(10, 45)
            self.pidGraphWidget.setYRange(-100, 100)
            self.breathGraphWidget.setYRange(0, 160)
            
            # Reset X ranges
            time_window = 60
            self.tempGraphWidget.setXRange(0, time_window)
            self.pidGraphWidget.setXRange(0, time_window)
            self.breathGraphWidget.setXRange(0, time_window)
            
            self.log("📏 Graph scales reset to defaults (60s window)", "info")
            
        except Exception as e:
            self.log(f"❌ Error resetting graph scales: {e}", "error")

    def closeEvent(self, event):
        """Handle application close event"""
        try:
            # Stop timers
            self.status_request_timer.stop()
            if hasattr(self, 'sync_timer'):
                self.sync_timer.stop()
            
            # Disconnect serial
            if self.serial_manager.is_connected():
                self.serial_manager.disconnect()
            
            # Close loggers
            self.event_logger.close()

            self.log("👋 Application closing...")

            if hasattr(self, 'settings'):
                self.settings.setValue("splitters/vertical", self.vertical_splitter.sizes())
                self.settings.setValue("splitters/horizontal", self.main_splitter.sizes())

        except Exception as e:
            print(f"Error during shutdown: {e}")

        event.accept()

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Musehypothermi GUI")
    app.setApplicationVersion("2.0")
    
    # Set application style
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("Application interrupted by user")
        window.close()

if __name__ == "__main__":
    main()
