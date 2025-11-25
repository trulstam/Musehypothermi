# Musehypothermi Python Profile Loader Module - Final Harmonized Version
# Module: profile_loader.py

import csv
import json
import os
from typing import Dict, List

# Grenser for validering (justeres om nødvendig)
TEMP_MIN = -10
TEMP_MAX = 50
RAMP_MIN = 0
TIME_MIN = 0


class ProfileLoader:
    def __init__(self, event_logger=None):
        self.profile: List[Dict] = []
        self.event_logger = event_logger

    def load_profile(self, filepath: str) -> List[Dict]:
        """
        Load and validate a profile file (CSV or JSON).

        Returns a list of normalized profile steps with ``time_min`` and ``temp_c``
        fields. Optional keys include ``ramp_min`` and ``plate_target`` when
        derived from controller-ready step definitions.
        """

        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Profile file does not exist: {filepath}")

        extension = os.path.splitext(filepath)[1].lower()
        if extension == ".csv":
            profile_data = self._load_profile_csv(filepath)
        elif extension == ".json":
            profile_data = self._load_profile_json(filepath)
        else:
            raise ValueError("Unsupported profile format. Use CSV or JSON.")

        self.profile = profile_data

        if self.event_logger:
            filename = os.path.basename(filepath)
            self.event_logger.log_event(
                f"PROFILE_LOADED file={filename} steps={len(self.profile)}"
            )

        return self.profile

    # --- Backward-compatible public helpers used by GUI/TestSuite ---
    def load_profile_json(self, filepath: str) -> bool:
        """Load a JSON profile and store it on the instance.

        Returns
        -------
        bool
            ``True`` on success, ``False`` on validation or IO failure.
        """

        try:
            self.profile = self._load_profile_json(filepath)

            if self.event_logger:
                filename = os.path.basename(filepath)
                self.event_logger.log_event(
                    f"PROFILE_LOADED file={filename} steps={len(self.profile)}"
                )

            return True

        except Exception as exc:
            print(f"❌ Failed to load JSON profile '{filepath}': {exc}")
            if self.event_logger:
                self.event_logger.log_event(
                    f"PROFILE_LOAD_FAILED file={filepath} error={exc}"
                )
            return False

    def load_profile_csv(self, filepath: str) -> bool:
        """Load a CSV profile and store it on the instance.

        Returns
        -------
        bool
            ``True`` on success, ``False`` on validation or IO failure.
        """

        try:
            self.profile = self._load_profile_csv(filepath)

            if self.event_logger:
                filename = os.path.basename(filepath)
                self.event_logger.log_event(
                    f"PROFILE_LOADED file={filename} steps={len(self.profile)}"
                )

            return True

        except Exception as exc:
            print(f"❌ Failed to load CSV profile '{filepath}': {exc}")
            if self.event_logger:
                self.event_logger.log_event(
                    f"PROFILE_LOAD_FAILED file={filepath} error={exc}"
                )
            return False

    def _load_profile_csv(self, filepath: str) -> List[Dict]:
        """Load and normalize a temperature profile from a CSV file."""
        profile_data: List[Dict] = []

        with open(filepath, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            for idx, row in enumerate(reader):
                if not row or row[0].strip().startswith("#"):
                    continue  # Hopp over kommentarer eller tomme linjer

                if len(row) < 2:
                    raise ValueError(f"Line {idx + 1} must include time and temperature")

                time_min = float(row[0].strip())
                temp_c = float(row[1].strip())
                ramp_min = float(row[2].strip()) if len(row) > 2 else 0.0

                self._validate_entry(idx, time_min, temp_c, ramp_min)

                profile_data.append(
                    {
                        "time_min": time_min,
                        "temp_c": temp_c,
                        "ramp_min": ramp_min,
                    }
                )

        if not profile_data:
            raise ValueError("CSV file did not contain any profile rows")

        return profile_data

    def _load_profile_json(self, filepath: str) -> List[Dict]:
        """Load and normalize a temperature profile from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError("Profile JSON must contain a list of steps")

        if not data:
            raise ValueError("JSON profile is empty")

        # Detect controller-ready structure (plate_* fields) and convert to
        # timeline points. Otherwise, accept time-based entries directly.
        controller_keys = {"plate_start_temp", "plate_end_temp", "total_step_time_ms"}
        profile_data: List[Dict] = []

        if controller_keys.issubset(data[0].keys() if isinstance(data[0], dict) else {}):
            profile_data = self._convert_controller_steps_to_points(data)
        else:
            for idx, entry in enumerate(data):
                if not isinstance(entry, dict):
                    raise ValueError(f"Entry {idx + 1} must be an object")

                if "time_min" not in entry or "temp_c" not in entry:
                    raise ValueError(
                        f"Entry {idx + 1} must include 'time_min' and 'temp_c'"
                    )

                time_min = float(entry.get("time_min"))
                temp_c = float(entry.get("temp_c"))
                ramp_min = float(entry.get("ramp_min", 0))

                self._validate_entry(idx, time_min, temp_c, ramp_min)

                point = {
                    "time_min": time_min,
                    "temp_c": temp_c,
                }

                if ramp_min:
                    point["ramp_min"] = ramp_min

                if "plate_target" in entry:
                    point["plate_target"] = float(entry["plate_target"])

                profile_data.append(point)

        return profile_data

    def _convert_controller_steps_to_points(self, steps: List[Dict]) -> List[Dict]:
        """
        Convert controller-ready steps to normalized profile points.

        The resulting timeline starts at t=0 with the first ``plate_start_temp``
        and adds an entry at the end of each step using ``plate_end_temp``.
        """

        profile_data: List[Dict] = []
        cumulative_time_min = 0.0

        for idx, entry in enumerate(steps):
            if not isinstance(entry, dict):
                raise ValueError(f"Entry {idx + 1} must be an object")

            plate_start = float(entry.get("plate_start_temp"))
            plate_end = float(entry.get("plate_end_temp"))
            ramp_time_ms = float(entry.get("ramp_time_ms", 0))
            total_time_ms = float(entry.get("total_step_time_ms"))
            rectal_target = entry.get("rectal_override_target", -1000)
            rectal_target = float(rectal_target) if rectal_target is not None else -1000.0

            self._validate_step_entry(
                idx,
                plate_start,
                plate_end,
                ramp_time_ms,
                total_time_ms,
                rectal_target,
            )

            if not profile_data:
                # First point uses the starting plate temperature.
                self._validate_entry(idx, cumulative_time_min, plate_start, 0)
                profile_data.append(
                    {
                        "time_min": cumulative_time_min,
                        "temp_c": plate_start,
                        "ramp_min": 0.0,
                    }
                )

            total_time_min = total_time_ms / 60000.0
            ramp_min = ramp_time_ms / 60000.0
            cumulative_time_min += total_time_min

            self._validate_entry(idx, cumulative_time_min, plate_end, ramp_min)

            profile_data.append(
                {
                    "time_min": cumulative_time_min,
                    "temp_c": plate_end,
                    "ramp_min": ramp_min,
                    "plate_target": plate_end,
                }
            )

        return profile_data

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

                if self.profile and {"time_min", "temp_c", "ramp_min"}.issubset(
                    self.profile[0].keys()
                ):
                    writer.writerow(["# Time(min)", "Temperature(C)", "Ramp(min)"])

                    for step in self.profile:
                        writer.writerow([
                            step["time_min"],
                            step["temp_c"],
                            step["ramp_min"]
                        ])
                else:
                    writer.writerow(
                        [
                            "# plate_start_temp",
                            "plate_end_temp",
                            "ramp_time_ms",
                            "rectal_override_target",
                            "total_step_time_ms",
                        ]
                    )

                    for step in self.profile:
                        writer.writerow([
                            step.get("plate_start_temp"),
                            step.get("plate_end_temp"),
                            step.get("ramp_time_ms", 0),
                            step.get("rectal_override_target", -1000.0),
                            step.get("total_step_time_ms"),
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
            if {"time_min", "temp_c", "ramp_min"}.issubset(step.keys()):
                print(
                    f"  ➡️ Time: {step['time_min']} min, Temp: {step['temp_c']}°C, Ramp: {step['ramp_min']} min"
                )
            else:
                print(
                    "  ➡️ Start: {start}°C, End: {end}°C, Ramp: {ramp} ms, Hold: {hold} ms, Rectal: {rectal}".format(
                        start=step.get("plate_start_temp"),
                        end=step.get("plate_end_temp"),
                        ramp=step.get("ramp_time_ms", 0),
                        hold=step.get("total_step_time_ms"),
                        rectal=step.get("rectal_override_target", -1000.0),
                    )
                )

    def _validate_entry(self, idx, time_min, temp_c, ramp_min):
        """Internal validation for each step entry."""
        if time_min < TIME_MIN:
            raise ValueError(f"Time ({time_min}) cannot be below {TIME_MIN} min")

        if not (TEMP_MIN <= temp_c <= TEMP_MAX):
            raise ValueError(f"Temperature ({temp_c}°C) out of range ({TEMP_MIN}°C to {TEMP_MAX}°C)")

        if ramp_min < RAMP_MIN:
            raise ValueError(f"Ramp ({ramp_min}) cannot be below {RAMP_MIN} min")

    def _validate_step_entry(
        self,
        idx,
        plate_start,
        plate_end,
        ramp_time_ms,
        total_time_ms,
        rectal_target,
    ):
        """Validation for controller-ready step definitions."""

        for temp_value, label in (
            (plate_start, "plate_start_temp"),
            (plate_end, "plate_end_temp"),
        ):
            if not (TEMP_MIN <= temp_value <= TEMP_MAX):
                raise ValueError(
                    f"{label} ({temp_value}°C) out of range ({TEMP_MIN}°C to {TEMP_MAX}°C)"
                )

        if rectal_target != -1000.0 and not (TEMP_MIN <= rectal_target <= TEMP_MAX):
            raise ValueError(
                f"rectal_override_target ({rectal_target}°C) out of range ({TEMP_MIN}°C to {TEMP_MAX}°C)"
            )

        if total_time_ms <= 0:
            raise ValueError("total_step_time_ms must be positive")

        if ramp_time_ms < 0:
            raise ValueError("ramp_time_ms cannot be negative")

        if ramp_time_ms > total_time_ms:
            raise ValueError("ramp_time_ms cannot exceed total_step_time_ms")
