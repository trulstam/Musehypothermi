import serial
import serial.tools.list_ports
import json
import threading
import time

class SerialManager:
    def __init__(self, port=None, baud=115200, heartbeat_interval=2, failsafe_timeout=5):
        self.port = port
        self.baud = baud
        self.heartbeat_interval = heartbeat_interval
        self.failsafe_timeout = failsafe_timeout

        self.ser = None

        # States
        self.keep_running = False
        self.last_heartbeat_time = time.time()
        self.last_data_time = time.time()
        self.failsafe_triggered = False
        self.latest_data = None

        # Optional callback
        self.on_data_received = None

    def connect(self, port):
        self.port = port
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            print(f"✅ Connected to {self.port} at {self.baud} baud.")
        except serial.SerialException as e:
            print(f"❌ Error opening serial port: {e}")
            self.ser = None
            return False

        # Start threads
        self.keep_running = True
        self.read_thread = threading.Thread(target=self.read_serial_loop, daemon=True)
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat_loop, daemon=True)
        self.read_thread.start()
        self.heartbeat_thread.start()

        return True

    def disconnect(self):
        self.keep_running = False
        print("🛑 Disconnecting SerialManager...")

        if hasattr(self, 'read_thread') and self.read_thread.is_alive():
            self.read_thread.join(timeout=1)
        if hasattr(self, 'heartbeat_thread') and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1)

        if self.ser and self.ser.is_open:
            self.ser.close()
            print("✅ Disconnected.")

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def list_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def send(self, message):
        if not self.is_connected():
            print("❌ Serial port not available.")
            return
        try:
            json_cmd = message + "\n"
            self.ser.write(json_cmd.encode())
            print(f"➡️ Sent: {json_cmd.strip()}")
        except Exception as e:
            print(f"⚠️ Failed to send: {e}")

    def sendCMD(self, action, state):
        cmd = {"CMD": {"action": action, "state": state}}
        self.send(json.dumps(cmd))

    def sendSET(self, variable, value):
        cmd = {"SET": {"variable": variable, "value": value}}
        self.send(json.dumps(cmd))

    def read(self):
        if not self.is_connected():
            return None

        if self.ser.in_waiting:
            try:
                line = self.ser.readline().decode().strip()
                print(f"⬇️ Received: {line}")
                self.last_data_time = time.time()
                return line
            except Exception as e:
                print(f"⚠️ Error reading serial data: {e}")
        return None

    def read_serial_loop(self):
        while self.keep_running:
            line = self.read()
            if line and self.on_data_received:
                try:
                    data = json.loads(line)
                    self.latest_data = data
                    self.on_data_received(data)
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error: {e} → Line: {line}")

            if (time.time() - self.last_data_time > self.failsafe_timeout and
                not self.failsafe_triggered):
                self.trigger_failsafe()

            time.sleep(0.05)

    def send_heartbeat_loop(self):
        while self.keep_running:
            if self.is_connected():
                self.sendCMD("heartbeat", "ping")
            time.sleep(self.heartbeat_interval)

    def trigger_failsafe(self):
        self.failsafe_triggered = True
        print("🚨 Failsafe triggered! No data received in timeout period.")
        if self.on_data_received:
            self.on_data_received({"response": "Failsafe triggered"})

    def readData(self):
        return self.latest_data

    def close(self):
        self.disconnect()
        print("✅ SerialManager closed.")
