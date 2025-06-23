# Musehypothermi Python Profile Loader Module - Final Harmonized Version
# Module: profile_loader.py

import csv
import json
import os

# Grenser for validering (justeres om nødvendig)
TEMP_MIN = -10
TEMP_MAX = 50
RAMP_MIN = 0
TIME_MIN = 0

class ProfileLoader:
    def __init__(self, event_logger=None):
        self.profile = []
        self.event_logger = event_logger

    def load_profile_csv(self, filepath):
        """Load temperature profile from a CSV file."""
        self.profile.clear()

        try:
            with open(filepath, "r") as file:
                reader = csv.reader(file)
                for idx, row in enumerate(reader):
                    if not row or row[0].strip().startswith("#"):
                        continue  # Hopp over kommentarer eller tomme linjer

                    if len(row) < 3:
                        print(f"⚠️ Skipping line {idx + 1}: Insufficient columns.")
                        continue

                    try:
                        time_min = float(row[0].strip())
                        temp_c = float(row[1].strip())
                        ramp_min = float(row[2].strip())

                        self._validate_entry(idx, time_min, temp_c, ramp_min)

                        self.profile.append({
                            "time_min": time_min,
                            "temp_c": temp_c,
                            "ramp_min": ramp_min
                        })

                    except ValueError as ve:
                        print(f"⚠️ Validation error at line {idx + 1}: {ve}")

            msg = f"✅ CSV profile loaded: {filepath}"
            print(msg)
            if self.event_logger:
                self.event_logger.log_event(msg)
            return True

        except Exception as e:
            err = f"❌ Failed to load CSV profile '{filepath}': {e}"
            print(err)
            if self.event_logger:
                self.event_logger.log_event(err)
            return False

    def load_profile_json(self, filepath):
        """Load temperature profile from a JSON file."""
        self.profile.clear()

        try:
            with open(filepath, "r") as file:
                data = json.load(file)

                for idx, entry in enumerate(data):
                    try:
                        time_min = float(entry.get("time_min"))
                        temp_c = float(entry.get("temp_c"))
                        ramp_min = float(entry.get("ramp_min"))

                        self._validate_entry(idx, time_min, temp_c, ramp_min)

                        self.profile.append({
                            "time_min": time_min,
                            "temp_c": temp_c,
                            "ramp_min": ramp_min
                        })

                    except ValueError as ve:
                        print(f"⚠️ Validation error at entry {idx + 1}: {ve}")

            msg = f"✅ JSON profile loaded: {filepath}"
            print(msg)
            if self.event_logger:
                self.event_logger.log_event(msg)
            return True

        except Exception as e:
            err = f"❌ Failed to load JSON profile '{filepath}': {e}"
            print(err)
            if self.event_logger:
                self.event_logger.log_event(err)
            return False

    def export_profile_csv(self, filepath, metadata=None):
        """Export current profile to CSV."""
        if not self.profile:
            msg = "⚠️ No profile loaded to export."
            print(msg)
            if self.event_logger:
                self.event_logger.log_event(msg)
            return False

        try:
            with open(filepath, "w", newline="") as file:
                writer = csv.writer(file)
                # Skriv metadata som kommentarer (valgfritt)
                if metadata:
                    for key, value in metadata.items():
                        writer.writerow([f"# {key}: {value}"])

                writer.writerow(["# Time(min)", "Temperature(C)", "Ramp(min)"])

                for step in self.profile:
                    writer.writerow([
                        step["time_min"],
                        step["temp_c"],
                        step["ramp_min"]
                    ])

            msg = f"✅ Profile exported to CSV: {filepath}"
            print(msg)
            if self.event_logger:
                self.event_logger.log_event(msg)
            return True

        except Exception as e:
            err = f"❌ Failed to export CSV profile '{filepath}': {e}"
            print(err)
            if self.event_logger:
                self.event_logger.log_event(err)
            return False

    def export_profile_json(self, filepath):
        """Export current profile to JSON."""
        if not self.profile:
            msg = "⚠️ No profile loaded to export."
            print(msg)
            if self.event_logger:
                self.event_logger.log_event(msg)
            return False

        try:
            with open(filepath, "w") as file:
                json.dump(self.profile, file, indent=4)

            msg = f"✅ Profile exported to JSON: {filepath}"
            print(msg)
            if self.event_logger:
                self.event_logger.log_event(msg)
            return True

        except Exception as e:
            err = f"❌ Failed to export JSON profile '{filepath}': {e}"
            print(err)
            if self.event_logger:
                self.event_logger.log_event(err)
            return False

    def get_profile(self):
        """Return the loaded profile."""
        return self.profile

    def print_profile(self):
        """Pretty-print the currently loaded profile."""
        if not self.profile:
            print("⚠️ No profile loaded.")
            return

        print("📋 Loaded Temperature Profile:")
        for step in self.profile:
            print(f"  ➡️ Time: {step['time_min']} min, Temp: {step['temp_c']}°C, Ramp: {step['ramp_min']} min")

    def _validate_entry(self, idx, time_min, temp_c, ramp_min):
        """Internal validation for each step entry."""
        if time_min < TIME_MIN:
            raise ValueError(f"Time ({time_min}) cannot be below {TIME_MIN} min")

        if not (TEMP_MIN <= temp_c <= TEMP_MAX):
            raise ValueError(f"Temperature ({temp_c}°C) out of range ({TEMP_MIN}°C to {TEMP_MAX}°C)")

        if ramp_min < RAMP_MIN:
            raise ValueError(f"Ramp ({ramp_min}) cannot be below {RAMP_MIN} min")