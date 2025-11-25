# Musehypothermi firmware

### Temperature calibration (plate and rectal probe)

- Each sensor (cooling plate and rectal probe) has its own calibration table stored in EEPROM.
- A calibration point is a pair (measured, reference) in °C:
  - **measured** is read by the MCU from the selected sensor at the moment the command is received.
  - **reference** is a true value typed in manually by the user (external calibration thermometer, or any trusted reference).
- All reference values are **explicitly entered** in the GUI. The firmware never uses the plate reading as an automatic reference source.
- The firmware uses linear interpolation between calibration points to map measured → reference. Outside the calibrated range, values are clamped to the nearest endpoint.
- Calibration is configured via JSON:
  - `SET calibration_point { sensor, reference }` appends a point in RAM.
  - `SET calibration_commit { sensor, operator, timestamp }` saves the table and metadata to EEPROM.
- Metadata (timestamp + operator + number of points) is stored per sensor and exposed in the periodic status JSON.
