import sys
import json
import time
import csv
import os
import traceback

# Debug imports first
print("🔍 Starting GUI with Matplotlib...")

try:
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
    
    # Use matplotlib instead of pyqtgraph
    import matplotlib
    matplotlib.use('Qt5Agg')  # Use Qt backend
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    
    from framework.serial_comm import SerialManager
    from framework.event_logger import EventLogger
    from framework.profile_loader import ProfileLoader
    print("✅ All imports successful (using matplotlib)")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Try: pip install matplotlib")
    sys.exit(1)

class MatplotlibWidget(QWidget):
    """Custom matplotlib widget for Qt"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(12, 8), facecolor='white')
        self.canvas = FigureCanvas(self.figure)
        
        # Create subplot
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('Time (seconds)')
        self.ax.set_ylabel('Temperature (°C)')
        self.ax.set_title('Temperature Monitoring')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_facecolor('white')
        
        # Initialize empty lines
        self.line_plate, = self.ax.plot([], [], 'r-o', linewidth=3, markersize=6, label='Cooling Plate')
        self.line_rectal, = self.ax.plot([], [], 'g-s', linewidth=3, markersize=6, label='Rectal Probe')
        self.line_target, = self.ax.plot([], [], 'b--', linewidth=2, label='Target')
        
        self.ax.legend()
        
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        # Initial ranges
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(15, 45)
        
        self.canvas.draw()
        
        print("✅ Matplotlib widget created")

    def update_data(self, time_data, plate_data, rectal_data, target_data):
        """Update plot data"""
        try:
            # Update line data
            self.line_plate.set_data(time_data, plate_data)
            self.line_rectal.set_data(time_data, rectal_data)
            self.line_target.set_data(time_data, target_data)
            
            # Auto-scale if we have data
            if time_data and len(time_data) > 0:
                # X-axis
                x_min, x_max = min(time_data), max(time_data)
                self.ax.set_xlim(x_min - 1, x_max + 2)
                
                # Y-axis
                all_temps = []
                if plate_data:
                    all_temps.extend(plate_data)
                if rectal_data:
                    all_temps.extend(rectal_data)
                if target_data:
                    all_temps.extend(target_data)
                
                if all_temps:
                    y_min, y_max = min(all_temps), max(all_temps)
                    margin = (y_max - y_min) * 0.1 or 1
                    self.ax.set_ylim(y_min - margin, y_max + margin)
            
            # Redraw
            self.canvas.draw()
            return True
            
        except Exception as e:
            print(f"❌ Matplotlib update error: {e}")
            return False

    def clear_plot(self):
        """Clear all plot data"""
        self.line_plate.set_data([], [])
        self.line_rectal.set_data([], [])
        self.line_target.set_data([], [])
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(15, 45)
        self.canvas.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        print("🏗️ Initializing MainWindow with Matplotlib...")
        
        self.setWindowTitle("Musehypothermi GUI - Matplotlib Version")
        self.setMinimumSize(1000, 600)
        
        # Get screen size and adjust window accordingly
        screen = QApplication.primaryScreen().availableGeometry()
        width = min(1400, screen.width() - 100)
        height = min(900, screen.height() - 100)
        self.resize(width, height)

        # Initialize data structures first
        self.init_data()
        print("✅ Data structures initialized")

        # Initialize UI
        self.init_ui()
        print("✅ UI initialized")

        # Initialize managers
        self.init_managers()
        print("✅ Managers initialized")

    def init_data(self):
        """Initialize data structures"""
        self.profile_data = []
        self.last_data_time = time.time()
        self.start_time = None
        self.connection_established = False
        self.autotune_in_progress = False
        self.profile_active = False
        self.graph_mode = "live"

        # Graph data with detailed tracking
        self.graph_data = {
            "time": [],
            "plate_temp": [],
            "rectal_temp": [],
            "pid_output": [],
            "breath_rate": [],
            "target_temp": []
        }
        
        # Debug counters
        self.data_update_count = 0
        self.plot_update_count = 0

    def init_managers(self):
        """Initialize serial and logging managers"""
        try:
            self.serial_manager = SerialManager()
            self.serial_manager.on_data_received = self.process_incoming_data
            print("✅ SerialManager initialized")

            self.event_logger = EventLogger("gui_events")
            print("✅ EventLogger initialized")
            
            self.profile_loader = ProfileLoader(event_logger=self.event_logger)
            print("✅ ProfileLoader initialized")

            # Status request timer
            self.status_request_timer = QTimer()
            self.status_request_timer.timeout.connect(self.request_status)
            self.status_request_timer.start(3000)
            print("✅ Status timer started")

            # Auto-sync timer
            self.sync_timer = QTimer()
            self.sync_timer.setSingleShot(True)
            self.sync_timer.timeout.connect(self.initial_sync)
            print("✅ Sync timer initialized")
            
            # Populate ports
            self.refresh_ports()
            print("✅ Ports refreshed")
            
        except Exception as e:
            print(f"❌ Manager initialization error: {e}")
            traceback.print_exc()
            raise

    def init_ui(self):
        """Initialize user interface"""
        try:
            print("🎨 Creating UI layout...")
            
            # Create main widget
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # Use horizontal splitter for side-by-side layout
            main_splitter = QSplitter(Qt.Horizontal)
            central_widget_layout = QVBoxLayout()
            central_widget_layout.addWidget(main_splitter)
            central_widget.setLayout(central_widget_layout)
            
            # Left panel - Controls and Live Data
            left_panel = self.create_control_panel()
            left_panel.setMaximumWidth(400)
            main_splitter.addWidget(left_panel)
            
            # Right panel - Matplotlib Graph and Debug
            right_panel = self.create_graph_panel()
            main_splitter.addWidget(right_panel)
            
            # Set splitter proportions
            main_splitter.setSizes([400, 1000])
            
            print("✅ UI layout created")
            
        except Exception as e:
            print(f"❌ UI initialization error: {e}")
            traceback.print_exc()
            raise

    def create_control_panel(self):
        """Create control panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Connection section
        connection_group = QGroupBox("Serial Connection")
        connection_layout = QHBoxLayout()
        
        self.portSelector = QComboBox()
        self.portSelector.setFixedWidth(80)
        
        self.refreshButton = QPushButton("Refresh")
        self.refreshButton.clicked.connect(self.refresh_ports)
        
        self.connectButton = QPushButton("Connect")
        self.connectButton.clicked.connect(self.toggle_connection)
        
        self.connectionStatusLabel = QLabel("Disconnected")
        self.connectionStatusLabel.setStyleSheet("color: red; font-weight: bold;")
        
        connection_layout.addWidget(QLabel("Port:"))
        connection_layout.addWidget(self.portSelector)
        connection_layout.addWidget(self.refreshButton)
        connection_layout.addWidget(self.connectButton)
        connection_layout.addWidget(self.connectionStatusLabel)
        
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        # Live data section
        data_group = QGroupBox("Live Data")
        data_layout = QGridLayout()
        
        self.plateTempDisplay = QLabel("22.0°C")
        self.plateTempDisplay.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: red;")
        
        self.rectalTempDisplay = QLabel("37.0°C")
        self.rectalTempDisplay.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: green;")
        
        self.pidOutputDisplay = QLabel("0.0")
        self.pidOutputDisplay.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: purple;")
        
        self.targetTempDisplay = QLabel("37.0°C")
        self.targetTempDisplay.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: blue;")
        
        self.breathRateDisplay = QLabel("150 BPM")
        self.breathRateDisplay.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: orange;")
        
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
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # Control section
        control_group = QGroupBox("PID Control")
        control_layout = QVBoxLayout()
        
        # PID parameters
        pid_layout = QHBoxLayout()
        self.kpInput = QLineEdit("2.0")
        self.kpInput.setFixedWidth(60)
        self.kiInput = QLineEdit("0.5")
        self.kiInput.setFixedWidth(60)
        self.kdInput = QLineEdit("1.0")
        self.kdInput.setFixedWidth(60)
        
        self.setPIDButton = QPushButton("Set PID")
        self.setPIDButton.clicked.connect(self.set_pid_values)
        
        pid_layout.addWidget(QLabel("Kp:"))
        pid_layout.addWidget(self.kpInput)
        pid_layout.addWidget(QLabel("Ki:"))
        pid_layout.addWidget(self.kiInput)
        pid_layout.addWidget(QLabel("Kd:"))
        pid_layout.addWidget(self.kdInput)
        pid_layout.addWidget(self.setPIDButton)
        
        control_layout.addLayout(pid_layout)
        
        # Target temperature
        target_layout = QHBoxLayout()
        self.setpointInput = QLineEdit("37")
        self.setpointInput.setFixedWidth(60)
        self.setSetpointButton = QPushButton("Set Target")
        self.setSetpointButton.clicked.connect(self.set_manual_setpoint)
        
        target_layout.addWidget(QLabel("Target:"))
        target_layout.addWidget(self.setpointInput)
        target_layout.addWidget(self.setSetpointButton)
        target_layout.addStretch()
        
        control_layout.addLayout(target_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.startPIDButton = QPushButton("START PID")
        self.startPIDButton.clicked.connect(lambda: self.send_and_log_cmd("pid", "start"))
        self.startPIDButton.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        
        self.stopPIDButton = QPushButton("STOP PID")
        self.stopPIDButton.clicked.connect(lambda: self.send_and_log_cmd("pid", "stop"))
        self.stopPIDButton.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        
        self.panicButton = QPushButton("PANIC")
        self.panicButton.clicked.connect(self.trigger_panic)
        self.panicButton.setStyleSheet("background-color: darkred; color: white; font-weight: bold; font-size: 14px;")
        
        button_layout.addWidget(self.startPIDButton)
        button_layout.addWidget(self.stopPIDButton)
        button_layout.addWidget(self.panicButton)
        
        control_layout.addLayout(button_layout)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Debug stats
        debug_group = QGroupBox("Debug Stats")
        debug_layout = QFormLayout()
        
        self.dataCountLabel = QLabel("0")
        self.plotCountLabel = QLabel("0")
        self.dataPointsLabel = QLabel("0")
        
        debug_layout.addRow("Data Updates:", self.dataCountLabel)
        debug_layout.addRow("Plot Updates:", self.plotCountLabel)
        debug_layout.addRow("Data Points:", self.dataPointsLabel)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        layout.addStretch()
        return panel

    def create_graph_panel(self):
        """Create matplotlib graph panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Graph controls
        controls_layout = QHBoxLayout()
        
        self.testBasicPlotButton = QPushButton("Test Basic Plot")
        self.testBasicPlotButton.clicked.connect(self.test_basic_plot)
        self.testBasicPlotButton.setStyleSheet("background-color: #E91E63; color: white; font-weight: bold;")
        
        self.generateTestDataButton = QPushButton("Generate Test Data")
        self.generateTestDataButton.clicked.connect(self.generate_test_data)
        self.generateTestDataButton.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        
        self.clearGraphsButton = QPushButton("Clear Graphs")
        self.clearGraphsButton.clicked.connect(self.clear_graphs)
        self.clearGraphsButton.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        
        self.debugDataButton = QPushButton("Debug Data")
        self.debugDataButton.clicked.connect(self.debug_graph_data)
        self.debugDataButton.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        
        controls_layout.addWidget(self.testBasicPlotButton)
        controls_layout.addWidget(self.generateTestDataButton)
        controls_layout.addWidget(self.clearGraphsButton)
        controls_layout.addWidget(self.debugDataButton)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Matplotlib graph
        try:
            print("🎯 Creating matplotlib graph...")
            self.matplotlib_widget = MatplotlibWidget()
            layout.addWidget(self.matplotlib_widget)
            print("✅ Matplotlib graph created")
        except Exception as e:
            print(f"⚠️ Matplotlib graph creation failed: {e}")
            graph_label = QLabel("Matplotlib graph creation failed - check console")
            graph_label.setStyleSheet("background-color: lightgray; border: 1px solid black; min-height: 300px;")
            graph_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(graph_label)
        
        # Debug log
        debug_log_group = QGroupBox("Debug Log")
        debug_log_layout = QVBoxLayout()
        
        debug_controls = QHBoxLayout()
        self.clearDebugLogButton = QPushButton("Clear Debug Log")
        self.clearDebugLogButton.clicked.connect(lambda: self.debugLogBox.clear())
        
        self.autoScrollDebugCheckbox = QCheckBox("Auto-scroll")
        self.autoScrollDebugCheckbox.setChecked(True)
        
        debug_controls.addWidget(self.clearDebugLogButton)
        debug_controls.addWidget(self.autoScrollDebugCheckbox)
        debug_controls.addStretch()
        
        self.debugLogBox = QTextEdit()
        self.debugLogBox.setReadOnly(True)
        self.debugLogBox.setMaximumHeight(150)
        self.debugLogBox.setFont(QFont("Courier", 8))
        self.debugLogBox.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: 'Courier New';")
        
        debug_log_layout.addLayout(debug_controls)
        debug_log_layout.addWidget(self.debugLogBox)
        debug_log_group.setLayout(debug_log_layout)
        
        layout.addWidget(debug_log_group)
        
        # Event log
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout()
        
        self.logBox = QTextEdit()
        self.logBox.setReadOnly(True)
        self.logBox.setMaximumHeight(100)
        self.logBox.setFont(QFont("Courier", 9))
        
        log_layout.addWidget(self.logBox)
        log_group.setLayout(log_layout)
        
        layout.addWidget(log_group)
        
        return panel

    def debug_log(self, message):
        """Log to debug console"""
        # Get current time with milliseconds
        now = time.time()
        timestamp = time.strftime("%H:%M:%S", time.localtime(now))
        milliseconds = int((now % 1) * 1000)
        full_timestamp = f"{timestamp}.{milliseconds:03d}"
        formatted_message = f"[{full_timestamp}] {message}"
        
        print(f"MATPLOTLIB_DEBUG: {message}")
        
        try:
            self.debugLogBox.append(formatted_message)
            if self.autoScrollDebugCheckbox.isChecked():
                scrollbar = self.debugLogBox.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except:
            pass

    def test_basic_plot(self):
        """Test basic plotting with matplotlib"""
        try:
            self.debug_log("🧪 Starting matplotlib basic plot test...")
            
            # Clear existing data
            self.matplotlib_widget.clear_plot()
            self.debug_log("🧹 Cleared existing plot data")
            
            # Create simple test data
            x_data = [0, 1, 2, 3, 4, 5]
            y_data_plate = [20, 25, 30, 35, 40, 45]
            y_data_rectal = [37, 36, 35, 34, 33, 32]
            y_data_target = [25, 25, 25, 25, 25, 25]
            
            self.debug_log(f"📊 Test data created:")
            self.debug_log(f"  X: {x_data}")
            self.debug_log(f"  Plate: {y_data_plate}")
            self.debug_log(f"  Rectal: {y_data_rectal}")
            self.debug_log(f"  Target: {y_data_target}")
            
            # Update matplotlib widget
            success = self.matplotlib_widget.update_data(x_data, y_data_plate, y_data_rectal, y_data_target)
            
            if success:
                self.debug_log("✅ Matplotlib plot updated successfully")
                self.log("✅ Basic matplotlib plot test completed successfully", "success")
            else:
                self.debug_log("❌ Matplotlib plot update failed")
                self.log("❌ Basic matplotlib plot test failed", "error")
            
        except Exception as e:
            error_msg = f"❌ Basic plot test error: {e}"
            self.debug_log(error_msg)
            self.log(error_msg, "error")
            traceback.print_exc()

    def generate_test_data(self):
        """Generate test data with matplotlib"""
        try:
            self.debug_log("🎲 Generating comprehensive test data...")
            
            # Clear graphs first
            self.clear_graphs()
            
            import math
            
            # Generate 30 data points
            times = list(range(30))
            plate_temps = [22 + 5 * math.sin(i/5) + i/10 for i in times]
            rectal_temps = [37 - i/10 + math.sin(i/3) for i in times]
            target_temps = [25 + 5 * math.sin(i/8) for i in times]
            
            self.debug_log(f"📊 Generated {len(times)} data points")
            
            # Store in graph_data
            self.graph_data = {
                "time": times,
                "plate_temp": plate_temps,
                "rectal_temp": rectal_temps,
                "pid_output": [0] * len(times),
                "breath_rate": [150] * len(times),
                "target_temp": target_temps
            }
            
            self.debug_log("💾 Data stored in graph_data structure")
            
            # Update matplotlib graph
            success = self.update_matplotlib_graphs()
            
            if success:
                # Update displays
                self.plateTempDisplay.setText(f"{plate_temps[-1]:.1f}°C")
                self.rectalTempDisplay.setText(f"{rectal_temps[-1]:.1f}°C")
                self.targetTempDisplay.setText(f"{target_temps[-1]:.1f}°C")
                
                self.debug_log("✅ Test data generation completed")
                self.log("✅ Test data generated successfully", "success")
            else:
                self.debug_log("❌ Test data generation failed")
                self.log("❌ Test data generation failed", "error")
            
        except Exception as e:
            error_msg = f"❌ Test data generation error: {e}"
            self.debug_log(error_msg)
            self.log(error_msg, "error")
            traceback.print_exc()

    def update_matplotlib_graphs(self):
        """Update matplotlib graphs with current data"""
        try:
            if not self.graph_data["time"]:
                self.debug_log("⚠️ No data to plot - graph_data is empty")
                return False
            
            data_points = len(self.graph_data["time"])
            self.debug_log(f"📊 Updating matplotlib with {data_points} data points")
            
            # Update matplotlib widget
            success = self.matplotlib_widget.update_data(
                self.graph_data["time"],
                self.graph_data["plate_temp"],
                self.graph_data["rectal_temp"],
                self.graph_data["target_temp"]
            )
            
            if success:
                # Update counters
                self.plot_update_count += 1
                self.plotCountLabel.setText(str(self.plot_update_count))
                self.dataPointsLabel.setText(str(data_points))
                
                self.debug_log(f"✅ Matplotlib update completed (update #{self.plot_update_count})")
                return True
            else:
                self.debug_log("❌ Matplotlib update failed")
                return False
            
        except Exception as e:
            error_msg = f"❌ Matplotlib update error: {e}"
            self.debug_log(error_msg)
            print(f"MATPLOTLIB_UPDATE_ERROR: {e}")
            traceback.print_exc()
            return False

    def clear_graphs(self):
        """Clear all graph data"""
        try:
            self.debug_log("🧹 Clearing all graph data...")
            
            # Clear matplotlib plot
            self.matplotlib_widget.clear_plot()
            
            # Clear internal data
            self.graph_data = {
                "time": [],
                "plate_temp": [],
                "rectal_temp": [],
                "pid_output": [],
                "breath_rate": [],
                "target_temp": []
            }
            
            # Reset counters
            self.data_update_count = 0
            self.plot_update_count = 0
            self.dataCountLabel.setText("0")
            self.plotCountLabel.setText("0")
            self.dataPointsLabel.setText("0")
            
            self.debug_log("✅ All graphs cleared")
            self.log("🧹 Graphs cleared", "info")
            
        except Exception as e:
            self.debug_log(f"❌ Clear graphs error: {e}")
            self.log(f"❌ Clear graphs error: {e}", "error")

    def debug_graph_data(self):
        """Debug current graph data structure"""
        try:
            self.debug_log("🔍 DEBUGGING CURRENT GRAPH DATA:")
            
            for key, values in self.graph_data.items():
                if values:
                    self.debug_log(f"  {key}: {len(values)} points, range {min(values):.2f} to {max(values):.2f}")
                    self.debug_log(f"    First 3: {values[:3]}")
                    self.debug_log(f"    Last 3: {values[-3:]}")
                else:
                    self.debug_log(f"  {key}: EMPTY")
            
            self.debug_log("🔍 MATPLOTLIB STATUS:")
            self.debug_log(f"  Canvas size: {self.matplotlib_widget.canvas.size()}")
            
        except Exception as e:
            self.debug_log(f"❌ Debug data error: {e}")

    def process_incoming_data(self, data):
        """Process incoming data with matplotlib updates"""
        if not data:
            return

        try:
            self.data_update_count += 1
            self.dataCountLabel.setText(str(self.data_update_count))
            
            # Log incoming data structure
            if self.data_update_count % 10 == 1:  # Log every 10th update to avoid spam
                self.debug_log(f"📥 Data update #{self.data_update_count}: {list(data.keys())}")
            
            # Update live displays
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

            # Update PID parameters
            if "pid_kp" in data and "pid_ki" in data and "pid_kd" in data:
                kp = data["pid_kp"]
                ki = data["pid_ki"]
                kd = data["pid_kd"]
                self.kpInput.setText(str(kp))
                self.kiInput.setText(str(ki))
                self.kdInput.setText(str(kd))

            # **LIVE GRAPH DATA UPDATES** - This is the key part!
            if self.graph_mode == "live" and self.connection_established:
                # Only add to live graph if we have actual sensor data
                if "cooling_plate_temp" in data and "anal_probe_temp" in data:
                    now = time.time()
                    if not self.start_time:
                        self.start_time = now
                        self.debug_log(f"🚀 Starting live data collection at {now}")
                    
                    elapsed = now - self.start_time
                    
                    # Add new data point
                    self.graph_data["time"].append(elapsed)
                    self.graph_data["plate_temp"].append(data["cooling_plate_temp"])
                    self.graph_data["rectal_temp"].append(data["anal_probe_temp"])
                    self.graph_data["pid_output"].append(data.get("pid_output", 0))
                    self.graph_data["breath_rate"].append(data.get("breath_freq_bpm", 0))
                    self.graph_data["target_temp"].append(data.get("plate_target_active", 37))
                    
                    # Log the data addition
                    if len(self.graph_data["time"]) % 5 == 1:  # Every 5th point
                        self.debug_log(f"📊 Added live data point #{len(self.graph_data['time'])}: "
                                     f"t={elapsed:.1f}s, plate={data['cooling_plate_temp']:.1f}°C, "
                                     f"rectal={data['anal_probe_temp']:.1f}°C")
                    
                    # Limit data to last 100 points for performance
                    max_points = 100
                    if len(self.graph_data["time"]) > max_points:
                        for key in self.graph_data:
                            self.graph_data[key] = self.graph_data[key][-max_points:]
                        self.debug_log(f"✂️ Trimmed data to last {max_points} points")
                    
                    # Update matplotlib graphs
                    self.update_matplotlib_graphs()

            # Handle events
            if "event" in data:
                event_msg = data["event"]
                self.log(f"📢 EVENT: {event_msg}", "info")
                try:
                    self.event_logger.log_event(event_msg)
                except:
                    pass  # Don't fail on logging errors

        except Exception as e:
            error_msg = f"❌ Data processing error: {e}"
            self.debug_log(error_msg)
            self.log(error_msg, "error")
            print(f"DATA_PROCESSING_ERROR: {e}")
            traceback.print_exc()

    def send_and_log_cmd(self, action, state):
        """Send command and log it"""
        if not self.serial_manager.is_connected():
            self.log("❌ Not connected - cannot send command", "error")
            return
            
        try:
            self.serial_manager.sendCMD(action, state)
            self.event_logger.log_event(f"CMD: {action} -> {state}")
            self.log(f"📡 Sent CMD: {action} = {state}", "command")
        except Exception as e:
            self.log(f"❌ Command send error: {e}", "error")

    def log(self, message, log_type="info"):
        """Enhanced logging"""
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
            scrollbar = self.logBox.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except:
            pass
        
        print(f"LOG: {message}")

    def set_pid_values(self):
        """Set PID values"""
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
            
            self.log(f"✅ Set PID: Kp={kp}, Ki={ki}, Kd={kd}", "success")
            
        except ValueError:
            self.log("❌ Invalid PID values", "error")
        except Exception as e:
            self.log(f"❌ PID set error: {e}", "error")

    def set_manual_setpoint(self):
        """Set manual setpoint"""
        try:
            value = float(self.setpointInput.text())
            
            if not self.serial_manager.is_connected():
                self.log("❌ Not connected", "error")
                return
                
            self.serial_manager.sendSET("target_temp", value)
            self.log(f"✅ Target set to {value:.1f}°C", "success")
            
        except ValueError:
            self.log("❌ Invalid target value", "error")
        except Exception as e:
            self.log(f"❌ Target set error: {e}", "error")

    def request_status(self):
        """Request status from Arduino"""
        try:
            if self.serial_manager.is_connected():
                self.serial_manager.sendCMD("get", "status")
        except Exception as e:
            print(f"Status request error: {e}")

    def trigger_panic(self):
        """Emergency panic"""
        try:
            if not self.serial_manager.is_connected():
                self.log("❌ Not connected", "error")
                return
                
            self.serial_manager.sendCMD("panic", "")
            self.log("🚨 PANIC TRIGGERED!", "error")
            QMessageBox.critical(self, "PANIC", "🚨 PANIC triggered!")
            
        except Exception as e:
            self.log(f"❌ Panic error: {e}", "error")

    def refresh_ports(self):
        """Refresh serial ports"""
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
                self.serial_manager.disconnect()
                self.connectButton.setText("Connect")
                self.connectionStatusLabel.setText("Disconnected")
                self.connectionStatusLabel.setStyleSheet("color: red; font-weight: bold;")
                self.log("🔌 Disconnected", "info")
                self.connection_established = False
                
                # Reset graph data when disconnecting
                self.start_time = None
                
            else:
                port = self.portSelector.currentText()
                if not port:
                    self.log("❌ No port selected", "error")
                    return
                    
                if self.serial_manager.connect(port):
                    self.connectButton.setText("Disconnect")
                    self.connectionStatusLabel.setText(f"Connected to {port}")
                    self.connectionStatusLabel.setStyleSheet("color: green; font-weight: bold;")
                    self.log(f"🔌 Connected to {port}", "success")
                    self.connection_established = True
                    
                    # Start sync
                    self.sync_timer.start(1000)
                else:
                    self.log(f"❌ Failed to connect to {port}", "error")
                    
        except Exception as e:
            self.log(f"❌ Connection error: {e}", "error")

    def initial_sync(self):
        """Initial sync after connection"""
        try:
            if self.serial_manager.is_connected():
                self.log("🔄 Syncing...", "info")
                QTimer.singleShot(500, self.request_status)
        except Exception as e:
            print(f"Sync error: {e}")

def main():
    """Main function with comprehensive error handling"""
    try:
        print("🚀 Starting Matplotlib GUI...")
        
        # Create QApplication
        app = QApplication(sys.argv)
        print("✅ QApplication created")
        
        # Set style
        app.setStyle('Fusion')
        print("✅ Style set to Fusion")
        
        # Create and show main window
        print("🏗️ Creating main window...")
        window = MainWindow()
        print("✅ Main window created")
        
        print("👁️ Showing window...")
        window.show()
        print("✅ Window shown")
        
        print("🔄 Starting event loop...")
        return app.exec()
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())