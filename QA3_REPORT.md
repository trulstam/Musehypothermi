## Musehypothermi – QA Round 3

### 1. Status-JSON Crosscheck
- Før endringer: GUI leste `failsafe_active`, `failsafe_reason`, profilfelter og equilibrium-flag; firmware sendte `failsafe`, manglet `panic_active`, `pid_mode` og equilibrium/statefelt i hurtigstatus, og profilstart blokkerte ikke failsafe/panic.
- Etter endringer: `sendStatus`/`sendData` rapporterer `failsafe_active`, `failsafe_reason`, `panic_active`, `panic_reason`, `pid_mode`, profilstatus (active/paused/step/remain) og equilibrium-feltene (`equilibrium_valid/temp/estimating/compensation_active`) som GUI forventer.

### 2. Failsafe / Panic Prioritet
- Implementert prioritet PANIC > FAILSAFE > AUTOTUNE > PROFILE > PID med harde stopp i PID/PWM og profilaborter.
- `panic`-kommando setter `panic_active=true`, nullstiller failsafe og stanser PID/autotune/profiler; `clear_panic` frigjør panic men holder alt stoppet.
- Failsafe stopper PID/autotune/profiler og holder PWM=0; panic overstyrer alltid failsafe.

Prioritetstabell:
- PANIC: PWM 0%, PID av, autotune/profil avbrutt, status `panic_active=true`, `failsafe_active=false`.
- FAILSAFE: PID av/PWM 0%, autotune/profil avbrutt, `failsafe_active=true`.
- AUTOTUNE: kan startes kun uten failsafe/panic, avbrytes av begge.
- PROFILE: blokkeres av failsafe/panic, avbrytes hvis disse trigges.
- PID: kjører kun når ingen høyere nivåer er aktive.

### 3. Equilibrium
- Lagt til statusfeltene `equilibrium_valid`, `equilibrium_temp`, `equilibrium_estimating`, `equilibrium_compensation_active` i sendStatus/sendData.
- PID-modulen nullstiller equilibrium under panic/failsafe og tilbyr testsetter for vertssimulering.

### 4. Profile Sikkerhet
- ProfileManager avviser lengder > MAX_STEPS og blokkerer start/resume når failsafe/panic er aktiv.
- Ved failsafe/panic stoppes profil, `current_step` settes til 0 og event logges.
- Testene bekrefter stegskifte og abortlogikk i simulert loop.

### 5. Firmware Host Tests
- Bygget med CMake i `main/tests_host/` (HOST_BUILD) og alle tre tester kjørte OK.
- Funn/fikser: la til host-stubber (EEPROM, pin-konstanter, String/ArduinoJson-minimaler), avgrenset autotune-JSON ved hostbygg, og sikret PWM-stopp i host.

### 6. Anbefaling før hardware
- Verifiser panic/failsafe-kommandoer på ekte hardware (PWM skal gå til 0 umiddelbart).
- Kjør GUI mot firmware for å bekrefte statusfelter (`panic_active`, equilibrium_*) vises korrekt.
- Test profilstart/resume-avbryt sekvens under sikkerhetsflagg.
- Sjekk at autotune blokkeres når failsafe/panic er aktiv.
- Kjør integrasjonstest etter installasjon av `libGL.so.1` for GUI.
- Monitorer event-logg for «Profile aborted due to …» og panic/failsafe meldinger.
- Bekreft at equilibrium-kompensasjon kan toggles og rapporteres i status.
- Hold HOST_BUILD-testene grønne ved fremtidige endringer i stubbene.
- Vurder hardware-watchdog for panic-clear før feltbruk.
