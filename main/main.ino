#include <Arduino.h>
#include "comm_api.h"
#include "task_scheduler.h"
#include "pid_module_asymmetric.h"
#include "sensor_module.h"
#include "pressure_module.h"
#include "eeprom_manager.h"
#include "system_config.h"
#include "pwm_module.h"

// Sett til true for å bruke den innebygde simulatoren under utvikling.
// Standard er live-modus for å unngå at simulasjonsdata når PID ved testing.
const bool USE_SIMULATION = false;
constexpr bool kEnablePwmScopeTest = true;

// === Eksterne moduler ===
AsymmetricPIDModule pid;
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
    pressure.begin();
    pid.begin(eeprom);

    if (kEnablePwmScopeTest) {
        pwmDebugDump();
    }

    // Start kommunikasjonsgrensesnitt + EEPROM factory reset-sjekk + events
    comm.begin(Serial, resetOccurred);

    // Init system tasks (heartbeat, failsafe, etc.)
    initTasks();

    if (USE_SIMULATION) {
        comm.sendEvent("🧪 Simulation mode enabled");
    } else {
        comm.sendEvent("🧊 Live hardware mode enabled");
    }

    // Send ferdig event til GUI
    comm.sendEvent("✅ Musehypothermi system initialized");
}

// === LOOP ===
void loop() {
    if (kEnablePwmScopeTest) {
        pwmSetDuty01(0.25f);
        delay(1000);
        pwmSetDuty01(0.75f);
        delay(1000);
        return;
    }

    runTasks();       // Oppdater sensorer, PID, profil, failsafe
    comm.process();   // Les og behandle innkommende kommandoer fra GUI
}
