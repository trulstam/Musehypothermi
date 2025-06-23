#include <Arduino.h>
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

    // Start Sensorer, Pustemonitor, PID-regulering
    sensors.begin();
    pressure.begin();
    pid.begin(eeprom);

    // Start kommunikasjonsgrensesnitt + EEPROM factory reset-sjekk + events
    comm.begin(Serial);

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
