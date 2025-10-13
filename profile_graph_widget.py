"""Profile graph popup widget for displaying profile data curves."""
from __future__ import annotations

from typing import Iterable, Mapping, Sequence, Tuple

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
import pyqtgraph as pg


class ProfileGraphPopup(QMainWindow):
    """Popup window that visualises temperature profile data."""

    def __init__(self, profile_data: Sequence[Mapping[str, float]] | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Profile Graph")
        self.resize(800, 600)

        self._plot_widget = pg.PlotWidget()
        self._plot_widget.showGrid(x=True, y=True)
        self._plot_widget.addLegend()
        self._plot_widget.setLabel("bottom", "Time", units="s")
        self._plot_widget.setLabel("left", "Temperature", units="°C")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self._plot_widget)
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._target_curve = self._plot_widget.plot(pen="c", name="Target Temp")
        self._actual_curve = self._plot_widget.plot(pen="m", name="Actual Temp")
        self._plate_curve = self._plot_widget.plot(pen="y", name="Plate Target")

        self.update_profile_data(profile_data or [])

    def update_profile_data(self, profile_data: Iterable[Mapping[str, float]]) -> None:
        """Refresh the graph with new profile data."""
        times: list[float] = []
        target_values: list[float] = []
        actual_values: list[float] = []
        plate_values: list[float] = []

        for point in profile_data:
            try:
                time_value = point.get("time")
                times.append(float(time_value if time_value is not None else len(times)))

                target_value = _first_present(
                    point,
                    ("temp", "targetTemp", "target", "targetTemperature"),
                )
                if target_value is None:
                    target_value = target_values[-1] if target_values else 0.0
                target_values.append(float(target_value))

                actual_value = _first_present(
                    point,
                    ("actual", "actualTemp", "temperature", "actualTemperature"),
                )
                if actual_value is None:
                    actual_value = target_values[-1]
                actual_values.append(float(actual_value))

                plate_value = _first_present(
                    point,
                    ("actualPlateTarget", "plateTarget", "plate", "plateTemperature"),
                )
                if plate_value is None:
                    plate_value = target_values[-1]
                plate_values.append(float(plate_value))
            except (TypeError, ValueError):
                # Skip malformed entries without interrupting the graph update.
                if times:
                    times.pop()
                    target_values.pop()
                    if actual_values:
                        actual_values.pop()
                    if plate_values:
                        plate_values.pop()
                continue

        self._target_curve.setData(times, target_values)
        self._actual_curve.setData(times, actual_values)
        self._plate_curve.setData(times, plate_values)

        self._actual_curve.setVisible(bool(actual_values))
        self._plate_curve.setVisible(bool(plate_values))


def _first_present(mapping: Mapping[str, float], keys: Tuple[str, ...]) -> float | None:
    """Return the first non-None value for *keys* in *mapping* if available."""

    for key in keys:
        if key in mapping:
            value = mapping[key]
            if value is not None:
                return value
    return None
