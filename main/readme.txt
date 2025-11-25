Denne branshen er "simulator på arduino" # Musehypothermi Dummy Simulation

## Formål

Denne README beskriver hvordan dummy-simuleringen av Musehypothermi-systemet fungerer. Hensikten er å tillate utvikling og testing av programvare på Arduino Uno R4 Minima uten at fysiske sensorer eller kjøleenheter er koblet til. Dummyen gir realistisk simulert oppførsel, slik at GUI, PID-regulering, failsafe-systemer og eksperimentprofiler kan testes.

---

## Overordnet systemarkitektur

- **Simulerte signaler**: Temperatur- og pustedata beregnes som en funksjon av PID-output og definert fysiologi.
- **Ingen ekte sensorer**: Alle `analogRead()`-kall returnerer data kun brukt for støytillegg.
- **Systemkommunikasjon**: Kommunikasjon mellom Arduino og GUI via eksisterende USB-serial (pyserial).
- **Failsafe**: Simulert pust kan stoppe → triggers failsafe hvis aktivert i `runTasks()`.

---

## Simulerte komponenter

### Cooling Plate Temperatur
- **Starter** ved 22°C (romtemperatur).
- **Påvirkes av**:
  - PID PWM-output (fra `pid.getPwmOutput()`).
  - Varmelekkasje til omgivelsene (romtemp = 22°C).
- **Fysikkparametre**:
  - Termisk masse: **0.3 kg** (plate + Peltier).
  - Spesifikk varme: **900 J/(kg·K)**.
  - Varmelekkasje: **0.01** proporsjonal faktor.
- **Effekt fra PID**:
  - PWM-output: -2399 til +2399.
  - Skaleres til -120W til +120W.

### Rectal Temperatur (Kjernetemp)
- **Starter** ved 37°C.
- **Påvirkes av**:
  - Varmeledning fra kjøleplate.
  - Intern metabolisme.
- **Fysikkparametre**:
  - Termisk masse: **0.03 kg** (mus på 30 g).
  - Spesifikk varme: **3470 J/(kg·K)**.
  - Varmeoverføring (plate → rektum): **0.02** proporsjonal faktor.
- **Metabolisme**:
  - 0.21 W ved 37°C.
  - Ned til 0.01 W ved 14°C.

---

## PID-regulering

### PID-input
- **Bruker kjøleplate-temperatur som input** for PID-reguleringen.
- PID holder platen på målt **targetTemp** (fra profiler eller GUI).

### Rektal temperatur som begrensning
- Hvis **rectal_override_target** er satt i et profil-steg:
  - Hvis rektal temperatur synker **under dette målet**, økes plate-setpunktet med en margin.
  - Ellers ignoreres rektaltemperaturen.

---

## Pustefrekvens (Breath Rate)
- **Starter** på 150 BPM.
- **Synker med rektaltemperatur**:
  - Over 16°C: Lineær fall fra 150 BPM til 1.5 BPM.
  - Mellom 16°C og 14°C: Kvadratisk fall mot null.
  - Under 14°C: 0 BPM → apné / "klinisk død".

### Støy
- `analogRead(A4)` på åpen pin gir tilfeldig variasjon:
  - Mappes til ±0.5 BPM.

### Failsafe
- Hvis pust < 1 BPM (eller eksakt 0 BPM), bør failsafe trigges i `runTasks()`:
```cpp
if (pressure.getBreathRate() < 1.0) {
    triggerFailsafe("no_breathing_detected");
}
```

---

## Støy i temperaturmålinger
- `analogRead(A3)` på åpen pin gir tilfeldig variasjon:
  - Mappes til ±0.05°C.
- Legges på både `coolingPlateTemp` og `rectalTemp` etter simulert fysikk.

---

## Viktige antagelser

1. **PID input**: Bruker **Cooling Plate Temp** som input for PID-reguleringen. Dette er den korrekte implementasjonen i henhold til systemdesignet.

2. **Rektal temperatur fungerer kun som en begrensning av PID setpoint** når dette er definert i en profil.

3. **PWM output**: Styres av PID-regulator, som påvirker simulert platetemperatur. Det er **PWM-verdien** som i realitet ville påvirket Peltier, men her brukes til simulering.

4. **Failsafe**: Apné er den primære triggeren, men du kan også overvåke temperaturer for å sette egne grenser.

---

## Funksjonelle detaljer

| Parameter                | Verdi                           |
|--------------------------|---------------------------------|
| Plate termisk masse      | 0.3 kg                         |
| Plate spesifikk varme    | 900 J/(kg·K)                   |
| Plate varmetap faktor    | 0.01                           |
| Mus termisk masse        | 0.03 kg                        |
| Mus spesifikk varme      | 3470 J/(kg·K)                  |
| Mus-plate kobling        | 0.02                           |
| Metabolisme (14-37°C)    | 0.01W → 0.21W                  |
| PWM-output område        | -2399 til +2399 (skalert til ±120W) |
| Romtemperatur            | 22°C                           |
| Plate begrensning        | -10°C til +50°C                |
| Rektal begrensning       | 14°C til 40°C                  |
| Pustefrekvens            | 150 BPM → 0 BPM (ved 14°C)     |

---

## Feilsøking og etterprøvbarhet

- **Simulerte måleverdier er deterministiske** gitt:
  - PWM output fra PID.
  - Oppdateringsintervall (`deltaTime`).
- **Støykomponentene** fra ADC gir variabilitet.
- **PID input er Cooling Plate Temp**, korrekt implementert.
- **Rektal temperatur styrer begrensninger i profil-steppene**, ikke direkte PID.

---

## Endringer i koden som må verifiseres

- `SensorModule::getCoolingPlateTemp()` brukes som PID-input.
- `PressureModule::getBreathRate()` brukes som failsafe-måling.
- `analogReference()` satt til `AR_EXTERNAL`, endres til `AR_DEFAULT` hvis ingen ekstern 4.096V AREF er koblet.

---

## Forslag til videre arbeid

1. Implementer test-profil for dummy som tar musa fra 37°C til 14°C og tilbake.
2. Loggfør `rectalTemp`, `coolingPlateTemp`, `pwmOutput`, `breathsPerMinute` for å verifisere simulering.
3. Evaluér PID-respons og profiler uten risiko for skade på forsøksdyr.

---

## Versjon
**Dummy Simuleringsmodell v1.0**
Dato: 2025-03-21
Ansvarlig: Truls & ChatGPT

## Updated Asymmetric PID Behavior (2025)

- Separate heating/cooling PID loops with ±0.3 °C deadband around SP.
- Heating is forcibly stopped once the plate reaches or exceeds the setpoint.
- Cooling near setpoint is reduced smoothly but never below 30% of the requested command.
- Feedforward (equilibrium compensation) is now **optional**: only active when
  `useEquilibriumCompensation == true`, equilibrium is valid, and the system is outside deadband.
- Autotune uses IMC tuning with lambda = max(0.5·τ, 2L, 5 s) and a global gain aggressiveness factor of 1.5.
- Output smoothing reduced (0.6 instead of 0.8) for faster control response.

