## 1. Flyttede/fjernede filer
- Fjernet host-sim- og stub-dublikatene i `main/` (`host_sim.cpp`, `host_arduino_stubs.h`, `Arduino.h`).
- Flyttet `host_firmware_stubs.h` inn i `main/host_sim/` sammen med de øvrige host-stubbene.

## 2. Oppdaterte includes
- Host-stubbene i `main/host_stubs/` peker nå på `../host_sim/host_firmware_stubs.h`.
- Host-simulatoren inkluderer kun `host_firmware_stubs.h`, som igjen trekker inn `host_arduino_stubs.h` (med `<thread>`/`<chrono>` og `std::this_thread::sleep_for`).
- Firmwarefilene bygger mot `<Arduino.h>` og unngår host-stubber i Arduino-bygget.

## 3. Host-sim struktur og bygg
- Alle host-stubber ligger i `main/host_sim/` (inkludert `Arduino_host.h`, `host_arduino_stubs.h`, `host_firmware_stubs.h`, `host_sim.cpp`).
- `CMakeLists.txt` samler host-sim-kildene, setter `cxx_std_17`, `-DHOST_BUILD`, og inkluderer både `main/` og `main/host_sim/` i include-path.

## 4. Verifikasjon
- Arduino-builden ser ikke lenger host-stubbene (ingen lokale `Arduino.h`/`host_*`-stub-headers i rot av `main/`).
- Host-simulatoren kan kompileres med f.eks.:
  ```
  g++ -std=c++17 -DHOST_BUILD -Imain -Imain/host_sim \
      -o host_sim main/host_sim/host_sim.cpp
  ```
- Ingen `std::this_thread`-relaterte feil – delay()-stubben bruker `std::this_thread::sleep_for(std::chrono::milliseconds(ms));` via `<thread>`/`<chrono>`.
