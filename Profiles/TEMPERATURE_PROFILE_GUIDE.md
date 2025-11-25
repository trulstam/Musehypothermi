# Temperaturprofil-format

Dette dokumentet beskriver hvordan temperaturprofiler for systemet defineres i JSON-filer. Hver profil består av en array med steg, der hvert steg angir hvordan plate- og rektaltemperatur skal utvikle seg over tid.

## Felt per steg
- `plate_start_temp`: Starttemperatur på platen i °C ved begynnelsen av steget.
- `plate_end_temp`: Sluttemperatur på platen i °C ved slutten av steget.
- `ramp_time_ms`: Tid i millisekunder systemet bruker på å gå fra `plate_start_temp` til `plate_end_temp` med lineær ramping. Bruk `0` dersom temperaturendringen skal skje umiddelbart.
- `rectal_override_target`: Måltemperatur i °C for rektal-proben når en override er aktiv. Sett til `-1000` når ingen rektal override skal brukes i steget.
- `total_step_time_ms`: Total tid i millisekunder steget varer, inkludert rampetid og eventuell holding på sluttemperaturen.

### Generelle retningslinjer
1. `plate_start_temp` bør matche forrige stegs `plate_end_temp` for å unngå hopp i profilen.
2. `total_step_time_ms` må være lik eller større enn `ramp_time_ms` slik at rampen får fullføre innenfor steget.
3. Bruk separate steg for hold-perioder hvis de skal skje på en stabil temperatur etter en ramp.
4. Sett `rectal_override_target` til en gyldig temperatur dersom rektaltemperaturen skal styres aktivt under steget; ellers bruk `-1000`.
5. Navngi profilfiler beskrivende, for eksempel `testprofil YYYY-MM-DD.json`, og plasser dem i `Profiles/`.

## Eksempel
Filen `testprofil 2025-11-25.json` viser en profil som starter på 37°C, kjøler ned i kontrollerte trinn, bruker rektal override ved 12°C–20°C, og varmer tilbake til 37°C med slutt-hold. Se filen for en konkret realisering av feltene over.
