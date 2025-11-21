# Musehypothermi – QA Round 1

## 1. Python compileall
- Kommando: `python -m compileall .`
- Resultat: OK
- Kommentarer: Alle Python-filer kompilerte uten syntaksfeil.

## 2. Python smoke test
- Script: `python tests/smoke_gui_serial.py`
- Resultat: FEIL
- Kommentarer: PySide6 import feilet pga. manglende systemavhengighet `libGL.so.1` i miljøet; ingen kodekrasj observert utover dette.

## 3. Signal/slot-sjekk
- Funn:
  - `SerialManager.data_received` (dict) → `MainWindow.process_incoming_data` (dict) – OK
  - `SerialManager.raw_line_received/sent` (str) → `MainWindow.on_serial_line` via lambda (retter retning, 1 arg) – OK
  - `SerialManager.failsafe_triggered` (uten args) → `MainWindow.on_pc_failsafe_triggered` (uten args) – OK
- Status: OK

## 4. Arduino kompileringsstatus
- Verktøy/kommando: arduino-cli ikke tilgjengelig i miljøet; kompilering ikke utført.
- Resultat: Ikke mulig
- Kommentarer: Manuell tørrsjekk av hovedfiler viste ingen åpenbare manglende deklarasjoner/definisjoner eller signaturmismatch; `comm_api` bruker `AsymmetricPIDModule` og profilopplasting-parsing er implementert.

## 5. Firmware-logisk vurdering
- Profiloverføring og arraygrenser: `CommAPI::handleCommand` bruker `StaticJsonDocument<3072>` og `parseProfile(JsonArray)` for opplasting; implementasjonen itererer arrayet sekvensielt uten out-of-bounds-tilgang.
- Autotune-/failsafe-/equilibrium-flagg: `AsymmetricPIDModule` nullstiller `equilibriumValid` ved ny estimering og sjekker flagget før bruk av kompensasjon; failsafe- og autotune-stater styres separat (f.eks. `setEmergencyStop`, `triggerFailsafe`, `startAutotune`) uten delte tellere.
- Status: OK for tørrsjekk; videre manuell/hardware-testing anbefales.
