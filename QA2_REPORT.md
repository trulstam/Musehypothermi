# Musehypothermi – QA Round 2

## 1. Integrasjonstest (mock Serial)
- Resultat: ❌ Ikke kjørt – PySide6 krever `libGL.so.1` som ikke er tilgjengelig i miljøet, og `apt-get` feilet pga. 403-block (ingen nett). Forsøkte både `QT_QPA_PLATFORM=offscreen` og `QT_OPENGL=software` uten effekt.
- Funksjoner testet: N/A (import stoppet før GUI kunne initialiseres)
- Feil funnet / rettet: Opprettet `tests/integration_mock_serial.py` med FakeSerialManager som emulerer statuspakker, logger og serial monitor, men kjøring ble blokkert av manglende systemavhengighet.
- Kommentarer: For å kjøre testen lokalt må `libGL.so.1` installeres (f.eks. `apt-get install libgl1` eller tilsvarende). Etter installasjon forventes skriptet å starte GUI-en uten å vise vindu og verifisere logging/event-håndtering.

## 2. GUI-verifisering
- Funn: `process_incoming_data` oppdaterer `failsafe_active`, `profile_active`, `profile_step_index`, `autotune_active`, `equilibrium_valid`, `equilibrium_temp` og relaterte etiketter. Data logger startes automatisk ved sensorpayload, og EventLogger loggfører failsafe-eventer.
- Signaler og slots: SerialManager-signaler kobles i `init_managers` (data_received → `process_incoming_data`, raw_line_* → `on_serial_line`, failsafe_triggered → dialog). Ingen nye manglende koblinger observert.
- Serial Monitor: `on_serial_line` skriver TX/RX-tekst til monitorfanen når signalene trigges; ingen blokkeringer identifisert i koden.

## 3. Host-simulation av firmware
- Kompileringsstatus: ✅ `g++ -std=c++17 -Imain/host_stubs -Imain -o /tmp/host_sim main/host_sim.cpp`
- Include-problemer: Løst via stub-headere (`Arduino.h`, `PID_v1.h`, `ArduinoJson.h`, PWM/Sensor/EEPROM/Comm`) slik at firmwarelogikk kan tørrkjøres uten Arduino toolchain.
- PID-resultater (oversikt): Simulert løkke starter på 25°C mot 37°C. Første linjer: `0 32.230 144.600`, `1 29.062 -61.922`, `2 31.461 48.796` (oscillerende, men demonstrerer at PID-stubben og termisk modell kjører).

## 4. Firmware-logikkinspeksjon
- Profil: `comm_api` starter/pause/resumer/stopper profiler via `profileManager`, men reliance på globale eksterner gjør racing mulig hvis `start()` kalles mens failsafe er aktiv – ingen eksplisitt blokkering observert.
- Autotune: `pid_module` aborterer autotune ved failsafe og ruller tilbake PID-verdier; statusflagg `autotuneActive` brukes i statusrapporten.
- Failsafe: PC-watchdog i `SerialManager` og firmware-kommandoer deler ansvar; GUI og firmware bruker samme `failsafe_active` felt. Potensiell risiko dersom GUI sender `panic` midt i profil/autotune – prioritering av stopp håndteres, men test på hardware anbefales.
- Equilibrium: GUI forventer `equilibrium_valid`, `equilibrium_temp`, `equilibrium_estimating` og `equilibrium_compensation_active`; firmware bør verifisere at alle felter sendes i statusjson for samsvar.

## 5. Anbefalinger før hardwaretest
- Installer `libGL.so.1` på testmaskin for å kjøre integrasjonstesten med FakeSerialManager.
- Verifiser status-json fra firmware inneholder `profile_active`, `profile_step_index`, `autotune_active`, `equilibrium_valid/temp`, `failsafe_active/reason` slik GUI forventer.
- Kjør manuell sekvens: start profil → pausér → resume → start autotune → avbryt → trigge failsafe → clear, og se at GUI-loggene matcher hendelsene.
- Test serial monitor under kontinuerlig statusspam for å sikre at UI ikke fryser.
- På firmware: bekreft at failsafe stoppe peltier uansett om profil/autotune er aktive og at flagg nullstilles etter clear.
