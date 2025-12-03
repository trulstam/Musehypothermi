# Musehypothermi Python Logger Module - Harmonized Version
# File: logger.py

import csv
import os
import json
import time
from datetime import datetime

# All auto-generated timestamps use this canonical format.
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now_ts():
    """Return the current timestamp using TIMESTAMP_FORMAT."""

    return datetime.now().strftime(TIMESTAMP_FORMAT)

class Logger:
    def __init__(
        self,
        filename_prefix="experiment",
        metadata=None,
        flush_every_n: int = 20,
        flush_interval_seconds: float = 5.0,
    ):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        directory = "logs"
        if not os.path.exists(directory):
            os.makedirs(directory)

        # CSV file setup
        self.filename_csv = os.path.join(directory, f"{filename_prefix}_{timestamp}.csv")
        self.csv_file = open(self.filename_csv, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)

        if metadata:
            for key, value in metadata.items():
                self.csv_writer.writerow([f"# {key}: {value}"])
        self.csv_writer.writerow(["timestamp", "cooling_plate_temp", "rectal_temp", "pid_output", "breath_freq_bpm", "comment"])

        print(f"✅ CSV logging to {self.filename_csv}")

        # JSON log setup
        self.filename_json = os.path.join(directory, f"{filename_prefix}_{timestamp}.json")
        self.json_content = {
            "metadata": metadata if metadata else {},
            "data": [],
            "comments": [],
            "events": []
        }
        self.flush_json()  # Oppretter filen første gang

        # Flush policy
        self.flush_every_n = max(1, flush_every_n)
        self.flush_interval_seconds = max(0.1, float(flush_interval_seconds))
        self._pending_rows = 0
        self._last_flush = time.monotonic()

        print(f"✅ JSON logging to {self.filename_json}")

    def log_data(self, data):
        timestamp = data.get("timestamp", _now_ts())

        row = [
            timestamp,
            data.get("cooling_plate_temp", "NaN"),
            data.get("anal_probe_temp", "NaN"),
            data.get("pid_output", "NaN"),
            data.get("breath_freq_bpm", "NaN"),
            ""
        ]

        # CSV log
        self.csv_writer.writerow(row)
        self._pending_rows += 1

        # JSON log
        self.json_content["data"].append({
            "timestamp": timestamp,
            "cooling_plate_temp": data.get("cooling_plate_temp", None),
            "rectal_temp": data.get("anal_probe_temp", None),
            "pid_output": data.get("pid_output", None),
            "breath_freq_bpm": data.get("breath_freq_bpm", None)
        })

        print(f"📥 Logged data at {timestamp}")
        self._maybe_flush()

    def log_comment(self, comment):
        now = _now_ts()
        row = [now, "", "", "", "", comment]

        self.csv_writer.writerow(row)
        self._pending_rows += 1

        self.json_content["comments"].append({
            "timestamp": now,
            "comment": comment
        })

        print(f"💬 Logged comment: {comment}")
        self._maybe_flush()

    def log_event(self, event):
        now = _now_ts()
        message = f"EVENT: {event}"

        self.csv_writer.writerow([now, "", "", "", "", message])
        self._pending_rows += 1

        self.json_content["events"].append({
            "timestamp": now,
            "event": event
        })

        print(f"⚡ Logged event: {event}")
        self._maybe_flush()

    def _maybe_flush(self):
        now = time.monotonic()
        if self._pending_rows >= self.flush_every_n or (now - self._last_flush) >= self.flush_interval_seconds:
            self.flush()

    def flush(self):
        if self._pending_rows == 0:
            return
        self.csv_file.flush()
        self.flush_json()
        self._pending_rows = 0
        self._last_flush = time.monotonic()

    def flush_json(self):
        with open(self.filename_json, "w") as file:
            json.dump(self.json_content, file, indent=4)

    def close(self):
        print("📝 Closing logger and writing JSON file...")
        self.flush()

        if self.csv_file:
            self.csv_file.close()

        print("✅ Logger closed.")
