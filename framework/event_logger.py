import csv
import os
import json
from datetime import datetime

# All auto-generated timestamps use this canonical format.
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now_ts():
    """Return the current timestamp using TIMESTAMP_FORMAT."""

    return datetime.now().strftime(TIMESTAMP_FORMAT)

class EventLogger:
    def __init__(self, filename_prefix="events", metadata=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        directory = "logs"
        os.makedirs(directory, exist_ok=True)

        self.closed = False

        # CSV setup
        self.filename_csv = os.path.join(directory, f"{filename_prefix}_{timestamp}.csv")
        self.csv_file = open(self.filename_csv, "w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)

        if metadata:
            for key, value in metadata.items():
                val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                self.csv_writer.writerow([f"# {key}: {val_str}"])

        self.csv_writer.writerow(["timestamp", "event"])
        print(f"✅ CSV event log initialized: {self.filename_csv}")

        # JSON setup
        self.filename_json = os.path.join(directory, f"{filename_prefix}_{timestamp}.json")
        self.json_content = {
            "metadata": metadata if metadata else {},
            "events": []
        }
        self.flush_json()
        print(f"✅ JSON event log initialized: {self.filename_json}")

    def log_event(self, event):
        """Log an event with timestamp."""
        now = _now_ts()
        try:
            self.csv_writer.writerow([now, event])
            self.csv_file.flush()

            self.json_content["events"].append({
                "timestamp": now,
                "event": event
            })

            print(f"⚡ Logged event: {event} at {now}")
            return True
        except Exception as e:
            print(f"❌ Failed to log event: {e}")
            return False

    def flush_json(self):
        """Write JSON buffer to file."""
        try:
            with open(self.filename_json, "w", encoding="utf-8") as file:
                json.dump(self.json_content, file, indent=4)
        except Exception as e:
            print(f"❌ Failed to flush JSON log: {e}")
            try:
                if self.csv_writer:
                    self.csv_writer.writerow([_now_ts(), f"[JSON flush error] {e}"])
                    self.csv_file.flush()
            except:
                pass

    def close(self):
        """Flush JSON and close files safely."""
        if self.closed:
            return
        print("📝 Closing event logger and flushing JSON...")
        self.flush_json()

        try:
            if self.csv_file:
                self.csv_file.close()
        except Exception as e:
            print(f"❌ Error closing CSV file: {e}")
        self.closed = True
        print("✅ Event logger closed.")

    def __del__(self):
        self.close()
