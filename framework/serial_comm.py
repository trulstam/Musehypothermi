import serial
import serial.tools.list_ports
import json
import threading
import time
import queue
from typing import Optional

from PySide6.QtCore import QObject, Signal


class SerialManager(QObject):
    data_received = Signal(dict)
    raw_line_received = Signal(str)
    raw_line_sent = Signal(str)
    failsafe_triggered = Signal()

    def __init__(
        self,
        port=None,
        baud=115200,
        heartbeat_interval=2,
        failsafe_timeout=5,
        write_timeout: Optional[float] = None,
    ):
        super().__init__()
        self.port = port
        self.baud = baud
        self.heartbeat_interval = heartbeat_interval
        self.failsafe_timeout = failsafe_timeout
        self.write_timeout = write_timeout

        self.ser = None
        self._write_lock = threading.Lock()
        self._send_queue: queue.Queue[str] = queue.Queue(maxsize=10)

        # States
        self.keep_running = False
        self.last_heartbeat_time = time.time()
        self.last_data_time = time.time()
        self.failsafe_triggered_flag = False
        self.latest_data = None
        self._on_data_received = None

    @property
    def on_data_received(self):
        return self._on_data_received

    @on_data_received.setter
    def on_data_received(self, callback):
        if self._on_data_received:
            try:
                self.data_received.disconnect(self._on_data_received)
            except (TypeError, RuntimeError):
                pass
        self._on_data_received = callback
        if callback:
            try:
                self.data_received.connect(callback)
            except TypeError as exc:
                print(f"⚠️ Failed to connect on_data_received callback: {exc}")

    def connect(self, port, write_timeout: Optional[float] = None):
        self.port = port
        if write_timeout is not None:
            self.write_timeout = write_timeout
        try:
            self.ser = serial.Serial(
                self.port,
                self.baud,
                timeout=1,
                write_timeout=self.write_timeout,
            )
            print(f"✅ Connected to {self.port} at {self.baud} baud.")
        except serial.SerialException as e:
            print(f"❌ Error opening serial port: {e}")
            self.ser = None
            return False

        # Start threads
        self.keep_running = True
        # Reset watchdog timers so we don't immediately trigger failsafe
        self.last_heartbeat_time = time.time()
        self.last_data_time = self.last_heartbeat_time
        self.failsafe_triggered_flag = False
        self.latest_data = None

        self.read_thread = threading.Thread(target=self.read_serial_loop, daemon=True)
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat_loop, daemon=True)
        self.sender_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.read_thread.start()
        self.heartbeat_thread.start()
        self.sender_thread.start()

        return True

    def disconnect(self):
        self.keep_running = False
        print("🛑 Disconnecting SerialManager...")

        if hasattr(self, 'read_thread') and self.read_thread.is_alive():
            self.read_thread.join(timeout=1)
        if hasattr(self, 'heartbeat_thread') and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1)
        if hasattr(self, 'sender_thread') and self.sender_thread.is_alive():
            self.sender_thread.join(timeout=1)

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
            return False
        json_cmd = message + "\n"

        try:
            self._send_queue.put(json_cmd, timeout=0.1)
            return True
        except queue.Full:
            print("⚠️ Send queue is full. Message dropped.")
            return False
        except Exception as e:
            print(f"⚠️ Failed to enqueue message: {e}")
            return False

    def sendCMD(self, action, state):
        cmd = {"CMD": {"action": action, "state": state}}

        # Any explicit failsafe clear command should reset the local watchdog flag
        # so the UI reflects that all failsafe triggers have been cleared.
        if (action == "failsafe" and state == "clear") or action == "failsafe_clear":
            self.failsafe_triggered_flag = False

        return self.send(json.dumps(cmd))

    def send_calibration_command(
        self, sensor: str, action: str, actual: Optional[float] = None
    ):
        """Send calibration-related commands following the serial protocol."""

        payload = {"CMD": {"action": "calibrate", "state": action, "sensor": sensor}}
        if actual is not None:
            payload["CMD"]["actual"] = actual

        return self.send(json.dumps(payload))

    def sendSET(self, variable, value):
        cmd = {"SET": {"variable": variable, "value": value}}
        return self.send(json.dumps(cmd))

    def read(self):
        if not self.is_connected():
            return None

        if self.ser.in_waiting:
            try:
                line = self.ser.readline().decode().strip()
                try:
                    self.raw_line_received.emit(line)
                except Exception:
                    pass
                print(f"⬇️ Received: {line}")
                self.last_data_time = time.time()
                return line
            except Exception as e:
                print(f"⚠️ Error reading serial data: {e}")
        return None

    def read_serial_loop(self):
        while self.keep_running:
            line = self.read()
            if line:
                try:
                    data = json.loads(line)
                    self.latest_data = data
                    self._queue_payload(data)
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error: {e} → Line: {line}")

            if (time.time() - self.last_data_time > self.failsafe_timeout and
                not self.failsafe_triggered_flag):
                self.trigger_failsafe()

            time.sleep(0.05)

    def _send_loop(self):
        while self.keep_running:
            try:
                json_cmd = self._send_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not self.is_connected():
                self._send_queue.task_done()
                continue

            try:
                try:
                    self.raw_line_sent.emit(json_cmd.strip())
                except Exception:
                    pass

                with self._write_lock:
                    self.ser.write(json_cmd.encode())
                print(f"➡️ Sent: {json_cmd.strip()}")
            except serial.SerialTimeoutException:
                print("⚠️ Serial write timed out. Clearing send queue to prevent blocking.")
                self._drain_send_queue()
            except Exception as e:
                print(f"⚠️ Failed to send: {e}")
            finally:
                self._send_queue.task_done()

    def send_heartbeat_loop(self):
        while self.keep_running:
            if self.is_connected():
                self.sendCMD("heartbeat", "ping")
            time.sleep(self.heartbeat_interval)

    def trigger_failsafe(self):
        self.failsafe_triggered_flag = True
        print("🚨 Failsafe triggered! No data received in timeout period.")
        try:
            self.failsafe_triggered.emit()
        except Exception:
            pass
        self._queue_payload(
            {
                "event": "Failsafe triggered (PC watchdog timeout)",
                "failsafe_active": True,
                "failsafe_reason": "pc_watchdog",
            },
            reset_failsafe=False,
        )

    def readData(self):
        return self.latest_data

    def close(self):
        self.disconnect()
        print("✅ SerialManager closed.")

    def _queue_payload(self, payload, *, reset_failsafe=True):
        if not isinstance(payload, dict):
            print("⚠️ Ignoring non-dict payload")
            return
        self.last_data_time = time.time()
        if reset_failsafe:
            self.failsafe_triggered_flag = False
        self.data_received.emit(dict(payload))

    def _drain_send_queue(self):
        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
                self._send_queue.task_done()
            except queue.Empty:
                break
