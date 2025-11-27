import json
import threading
import time
from typing import Any, Dict, List, Optional

import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, Signal


class SerialManager(QObject):
    """Qt-friendly serial manager with resilient threads and logging.

    The class emits signals for every raw line sent/received and for parsed
    JSON payloads. All worker loops are exception-safe so the GUI keeps
    running even if the device sends malformed data or the port glitches.
    """

    data_received = Signal(dict)
    raw_line_sent = Signal(str)
    raw_line_received = Signal(str)
    failsafe_triggered = Signal()

    def __init__(
        self,
        port: Optional[str] = None,
        baud: int = 115200,
        heartbeat_interval: float = 2.0,
        failsafe_timeout: float = 5.0,
    ) -> None:
        super().__init__()
        self.port = port
        self.baud = baud
        self.heartbeat_interval = heartbeat_interval
        self.failsafe_timeout = failsafe_timeout

        self.ser: Optional[serial.Serial] = None
        self.keep_running = False
        self.last_rx_time: float = 0.0
        self.failsafe_triggered_flag = False
        self.latest_data: Optional[Dict[str, Any]] = None

        self._on_data_received = None
        self._read_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._failsafe_thread: Optional[threading.Thread] = None
        self._ser_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Optional callback helper retained for compatibility with legacy code
    # that used ``serial_manager.on_data_received = ...``.
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    def list_ports(self) -> List[str]:
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self, port: str) -> bool:
        self.port = port
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            print(f"✅ Connected to {self.port} at {self.baud} baud")
            try:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                try:
                    # Toggle DTR to ensure Arduino reboot/bootloader reset where supported
                    self.ser.dtr = False
                    time.sleep(0.05)
                    self.ser.dtr = True
                except Exception:
                    pass
            except Exception as exc:
                print(f"⚠️ Unable to prime serial buffers: {exc}")
        except serial.SerialException as exc:
            print(f"❌ Error opening serial port: {exc}")
            self.ser = None
            return False

        self.keep_running = True
        self.last_rx_time = time.time()
        self.failsafe_triggered_flag = False

        self._read_thread = threading.Thread(
            target=self._read_loop, name="SerialReadThread", daemon=True
        )
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, name="HeartbeatThread", daemon=True
        )
        self._failsafe_thread = threading.Thread(
            target=self._failsafe_monitor_loop, name="FailsafeThread", daemon=True
        )

        self._read_thread.start()
        self._heartbeat_thread.start()
        self._failsafe_thread.start()

        return True

    def disconnect(self) -> None:
        self.keep_running = False
        print("🛑 Disconnecting SerialManager…")

        for thread in (self._read_thread, self._heartbeat_thread, self._failsafe_thread):
            if thread and thread.is_alive():
                thread.join(timeout=1)

        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception as exc:
                print(f"⚠️ Error closing serial port: {exc}")
        self.ser = None
        print("✅ Disconnected")

    def is_connected(self) -> bool:
        return bool(self.ser and self.ser.is_open)

    # ------------------------------------------------------------------
    # Transmission helpers
    # ------------------------------------------------------------------
    def _write_line(self, line_str: str) -> None:
        if not self.is_connected():
            print("❌ Serial port not available")
            return

        # Ensure a single trailing newline
        if not line_str.endswith("\n"):
            line_to_send = line_str + "\n"
        else:
            line_to_send = line_str

        try:
            with self._ser_lock:
                self.ser.write(line_to_send.encode("utf-8", errors="replace"))
            try:
                self.raw_line_sent.emit(line_to_send.rstrip("\n"))
            except Exception:
                pass
            print(f"➡️ Sent: {line_to_send.rstrip()}")
        except Exception as exc:
            print(f"⚠️ Failed to send line: {exc}")

    def send(self, message: str) -> None:
        """Send a pre-formatted JSON string over the serial link."""
        self._write_line(message)

    def sendCMD(self, action: str, state: Any, params: Optional[Dict[str, Any]] = None) -> None:
        cmd: Dict[str, Any] = {"CMD": {"action": action, "state": state}}
        if params is not None:
            cmd["CMD"]["params"] = params
        json_cmd = json.dumps(cmd, ensure_ascii=False)
        self._write_line(json_cmd)

    def sendSET(self, variable: str, value: Any) -> None:
        cmd = {"SET": {"variable": variable, "value": value}}
        json_cmd = json.dumps(cmd, ensure_ascii=False)
        self._write_line(json_cmd)

    # ------------------------------------------------------------------
    # Worker loops
    # ------------------------------------------------------------------
    def _read_loop(self) -> None:
        while self.keep_running:
            try:
                if not self.is_connected():
                    time.sleep(0.1)
                    continue

                raw_bytes = self.ser.readline()
                if not raw_bytes:
                    continue

                line = raw_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                # Emit every raw line regardless of JSON validity
                try:
                    self.raw_line_received.emit(line)
                except Exception:
                    pass

                self.last_rx_time = time.time()
                if self.failsafe_triggered_flag:
                    print("ℹ️ RX resumed after timeout")
                    self.failsafe_triggered_flag = False

                try:
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        self.latest_data = payload
                        self.data_received.emit(payload)
                    else:
                        print(f"⚠️ Ignoring non-dict JSON payload: {payload}")
                except json.JSONDecodeError as exc:
                    print(f"⚠️ JSON decode error: {exc}: {line}")
                except Exception as exc:
                    print(f"⚠️ Unexpected parse error: {exc}")
            except Exception as exc:
                print(f"⚠️ Serial read loop error: {exc}")
                time.sleep(0.1)

    def _heartbeat_loop(self) -> None:
        while self.keep_running:
            try:
                if self.is_connected():
                    self.sendCMD("heartbeat", "ping")
            except Exception as exc:
                print(f"⚠️ Heartbeat error: {exc}")
            time.sleep(self.heartbeat_interval)

    def _failsafe_monitor_loop(self) -> None:
        while self.keep_running:
            try:
                now = time.time()
                if (
                    self.is_connected()
                    and not self.failsafe_triggered_flag
                    and (now - self.last_rx_time) > self.failsafe_timeout
                ):
                    self.failsafe_triggered_flag = True
                    print("🚨 Failsafe triggered! No data received in timeout period.")
                    try:
                        self.failsafe_triggered.emit()
                    except Exception:
                        pass
            except Exception as exc:
                print(f"⚠️ Failsafe monitor error: {exc}")
            time.sleep(0.25)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def readData(self):
        """Retained for compatibility with older code paths."""
        return self.latest_data

    def close(self) -> None:
        self.disconnect()
        print("✅ SerialManager closed")
