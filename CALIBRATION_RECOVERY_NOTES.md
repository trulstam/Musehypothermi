# Calibration Recovery Notes

## Overview
- The calibration branch introduced table-based sensor calibration, new EEPROM fields, and expanded CommAPI/GUI commands. Those additions coincided with larger JSON payloads and layout shifts that destabilized serial communication.
- The recovery branch rolled back to the minimal, pre-calibration command set, restored the compact EEPROM layout, disabled calibration handling in SensorModule, and replaced the GUI calibration tab with a static notice. Communication and heartbeats are stable again with the smaller, well-defined JSON structures.

## Baseline: Recovery Branch State
### CommAPI
- Uses a shared `StaticJsonDocument<3072>` stored outside the stack for command parsing, keeping memory use predictable and avoiding stack exhaustion.
- Supported `CMD` actions: `pid` start/stop, `heartbeat` (responds with `"heartbeat_ack"`), `get` (`pid_params`/`data`/`status`/`config`), `profile` lifecycle, `failsafe_clear`, `panic`, `save_eeprom`, and `reset_config`. Other actions return `"unsupported_command"`.
- Supported `SET` variables: `target_temp`, heating PID gains, `pid_max_output`, `debug_level`, and `failsafe_timeout`; unknown variables return `"unsupported_command"`. Settings also persist target temp and failsafe timeout to EEPROM.
- Responses/events use small static documents per message type and always call `serializeJson(doc, *serial); serial->println();` to emit a single JSON object per line.
- Status/config/data payloads include core PID, safety, profile, and sensor readings only—no calibration fields—keeping payload sizes modest.

### EEPROMManager
- Stores only PID parameters (heating/cooling), target temperature, output limits, safety parameters, debug level, failsafe timeout, and a magic number; no calibration structures are present.
- Memory layout places the magic number immediately after failsafe timeout; additional fields were removed to keep offsets stable and compact.
- `factoryReset` writes defaults for PID, target temperature, output limits, safety, debug, and failsafe timeout, then writes the magic number.

### SensorModule
- Calibration tables are disabled; temperatures use raw ADC conversions plus optional offsets only.
- Provides accessors for cached temps and raw temps; setters only adjust simple offsets for compatibility.

### GUI
- Calibration tab replaced by a notice; add/commit/table/update functions are no-ops that log warnings, so no calibration messages are sent.
- Serial manager maintains resilient threads, heartbeats every 2s, and emits each raw line; uses simple `CMD`/`SET` wrappers matching the minimal firmware commands.

### Stability Patterns
- Shared static JSON buffer for parsing commands avoids per-call stack spikes (critical on AVR).
- All responses/events use dedicated static documents and explicit `serializeJson` + `println`, ensuring one JSON object per line for the GUI parser.
- GUI expects discrete responses/events and parses them as dicts; resilient read loop logs malformed JSON but keeps running, relying on predictable message framing.

## Calibration Branch: Problematic Changes
Comparing calibration-branch commit `c41e1e3` (around #207/#208) to recovery:

### CommAPI
- Switched to `StaticJsonDocument<3072>` allocated **inside** `handleCommand`, increasing stack usage on every call.
- Added many new `CMD` actions (`autotune`, asymmetric autotune, equilibrium, calibration table retrieval, failsafe status, PID tuning setters) and `SET` variables, expanding command surface and payload parsing complexity.
- Added calibration-specific `SET` payloads (`calibration_point`, `calibration_commit`) with nested objects and dual formats, increasing JSON size and branching.
- Status/config responses appended calibration metadata objects, enlarging payloads and altering expected keys.
- New `sendCalibrationTable` returned nested arrays of points plus metadata, using only a 1024-byte document, risking buffer overflow for larger tables.

### EEPROMManager
- Added calibration structures (`CalibrationPoint`, `SensorCalibrationMeta`) and EEPROM addresses for plate/rectal tables immediately after existing fields, moving the magic number and later values compared to recovery layout.
- `factoryReset` zeroed calibration metadata and tables in addition to PID/safety defaults, but still wrote the magic number at the shifted address.

### SensorModule
- Loaded calibration tables from EEPROM at startup and applied interpolation on every update, increasing CPU usage and coupling to EEPROM layout.
- Added mutable calibration state (tables, counts) and commit routines that write directly to EEPROM for plate/rectal/both sensors.

### GUI / Serial Manager
- Calibration tab sent `add_calibration_point`, `commit_calibration`, and `get_calibration_table` commands with nested payloads and expected table responses; also exported CSVs.
- Serial manager used a simpler heartbeat/watchdog loop but lacked the current per-line locking and newline normalization, making it more sensitive to framing issues.

**Classification**
- Likely to cause communication issues: in-function large `StaticJsonDocument`, expanded command set with nested payloads, calibration table responses approaching buffer limits, EEPROM layout shift (magic number moved), and GUI commands assuming larger responses.
- Safe/harmless but unfinished: data structures for calibration points/meta and SensorModule interpolation logic (algorithmically reasonable but needs safer integration).
- Purely GUI/UX: table rendering/export and operator/timestamp inputs.

## What Must Be Preserved from Recovery
- **Static command document outside the stack** to prevent RAM exhaustion during parsing.
- **Tight command set and predictable payloads** so the GUI’s simple dict parser and watchdog remain reliable.
- **Single-object-per-line serialization** via `serializeJson` + `println` for every response/event, maintaining clear framing.
- **Stable EEPROM layout with magic number position unchanged**; new calibration fields must be appended after existing addresses to avoid invalidating saved configs.
- **Sensor defaults that operate without calibration data**, ensuring valid temps and GUI operation even if calibration storage is empty.
- **GUI heartbeat/resilience** that tolerates malformed lines without crashing and distinguishes responses/events via simple keys like `"response"` or `"event"`.

## Usable Calibration Pieces
- Reusable as-is: calibration data structures (`CalibrationPoint`, `SensorCalibrationMeta`) and interpolation/apply logic in SensorModule (RAM-only) once decoupled from EEPROM layout risks.
- Needs redesign: CommAPI calibration commands must follow the recovery framing (shared static doc, compact payloads, consistent keys), and EEPROM layout should append calibration blocks after the current magic/fields rather than relocating them.
- Should be hardened: GUI calibration tab should validate responses and handle absent calibration gracefully instead of assuming table data; serial manager should retain the newer newline/locking behavior when sending calibration commands.

## Proposed Integration Strategy
1. **Phase 0 – Freeze baseline**
   - Tag current recovery state for reference.
   - Tests: basic connect/heartbeat, `get status/data/config`, profile start/stop roundtrip (manual GUI/serial console).

2. **Phase 1 – EEPROM layout (append-only)**
   - Append calibration meta + tables after existing safety/magic fields; keep magic number address unchanged.
   - Implement load/save calibration helpers only; do not wire to CommAPI/GUI yet.
   - Tests: boot with/without factory reset, verify existing settings load; inspect raw EEPROM offsets to confirm magic number still valid.

3. **Phase 2 – SensorModule calibration (RAM-first)**
   - Reintroduce calibration tables and interpolation; load from EEPROM if present, but default to passthrough when empty.
   - Ensure add/commit functions are internal and fail-safe when tables overflow.
   - Tests: unit-style firmware logs (manual) showing raw vs calibrated temps when tables are populated in code; confirm normal operation with empty tables.

4. **Phase 3 – CommAPI calibration commands (minimal, framed like recovery)**
   - Add a minimal `calibration` command namespace (e.g., `CMD` with `state` `get_table`/`add_point`/`commit`) using the shared static doc and small responses (consider pagination or per-sensor requests).
   - Responses should include a `type` discriminator (e.g., `"type": "calibration_table"`) and modest arrays to avoid buffer overruns.
   - Tests: serial-terminal sessions adding points and committing; verify stability alongside heartbeats and status streaming.

5. **Phase 4 – GUI calibration tab**
   - Re-enable UI elements with stricter error handling and matching JSON schema; reuse current SerialManager framing and locks.
   - Tests: end-to-end GUI runs (connect, add/commit, refresh table) while monitoring raw serial logs for malformed frames.

## Checklists & Pitfalls
- Always keep the shared command `StaticJsonDocument` global/static; avoid allocating kilobyte documents on the stack per call.
- When expanding EEPROM, append after existing addresses and preserve the magic number offset; perform version/magic checks before reading new sections.
- Bump JSON buffer sizes cautiously and keep calibration responses compact to stay within document capacity (large tables previously approached limits).
- Maintain one-JSON-object-per-line with `println` to prevent GUI framing errors.
- Ensure SensorModule continues to operate with empty calibration data; never assume tables are present at boot.
- In the GUI, guard against missing fields and decode errors; log and continue rather than crashing the read loop.
