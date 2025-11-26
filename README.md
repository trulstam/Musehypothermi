# Musehypothermi firmware

### Temperature calibration (cooling plate and rectal probe)

- Each sensor (cooling plate and rectal probe) has its own calibration table stored in EEPROM.
- A calibration point consists of:
  - `measured`: the raw temperature read by the MCU (in °C) at the moment the point is added.
  - `reference`: the true temperature in °C, typed in manually in the GUI from an external thermometer.
- The firmware uses piecewise linear interpolation between calibration points to map `measured → reference`. Outside the calibrated range, values are clamped to the nearest endpoint.
- Calibration is controlled via JSON over serial:
  - `SET: { "variable": "calibration_point", "value": { "sensor": "plate" | "rectal", "reference": <float> } }`
  - `SET: { "variable": "calibration_commit", "value": { "sensor": "plate" | "rectal" | "both", "operator": "<name>", "timestamp": <unix> } }`
- The GUI exposes a "Calibration" panel showing:
  - Raw vs calibrated temperature for both sensors with 4 decimal places.
  - Controls to add calibration points and commit tables, including operator name.
- Calibration metadata (timestamp, operator, number of points) is stored per sensor and reported in the periodic status JSON under the `calibration` object.

#### Kort veiledning for GUI-kalibrering

1. Stabiliser temperaturen på ønsket nivå før du starter.
2. Velg sensoren som skal kalibreres (plate eller rektal).
3. Sammenlign rå- og kalibrerte temperaturverdier i panelet.
4. Angi referansetemperaturen fra et eksternt termometer.
5. Klikk **Add Calibration Point** for å registrere punktet.
6. Gjenta steg 1–5 for flere punkter som dekker ønsket område.
7. Trykk **Commit Calibration** for å lagre tabellen.
8. Bruk **Export Calibration** for å hente ut kalibreringsdata ved behov.
