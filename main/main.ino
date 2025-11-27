// Sett til 1 for å kjøre innebygd simulering på Arduino, 0 for ekte sensorer
#ifndef SIMULATION_MODE
#define SIMULATION_MODE 0
#endif

#include "arduino_platform.h"

#include "comm_api.h"
#include "task_scheduler.h"
#include "pid_module.h"
#include "sensor_module.h"
#include "pressure_module.h"
#include "eeprom_manager.h"

// === Eksterne moduler ===
PIDModule pid;
SensorModule sensors;
PressureModule pressure;
EEPROMManager eeprom;
CommAPI comm(Serial);  // Serial interface (bruker Serial)

// === SETUP ===
void setup() {
    // Start Serial Interface (nødvendig for Serial objektet som brukes av CommAPI)
    Serial.begin(115200);
    delay(200);  // Stabiliser USB/Serial tilkobling (valgfritt)

    bool resetOccurred = eeprom.begin();

    // Start Sensorer, Pustemonitor, PID-regulering
    sensors.begin();
    sensors.loadCalibration(eeprom);
    pressure.begin();
    pid.begin(eeprom);

    // Start kommunikasjonsgrensesnitt + EEPROM factory reset-sjekk + events
    comm.begin(Serial, resetOccurred);

    // Init system tasks (heartbeat, failsafe, etc.)
    initTasks();

    // Send ferdig event til GUI
    comm.sendEvent("✅ Musehypothermi system initialized");
}

// === LOOP ===
void loop() {
    runTasks();       // Oppdater sensorer, PID, profil, failsafe
    comm.process();   // Les og behandle innkommende kommandoer fra GUI
}
