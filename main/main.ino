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
constexpr bool kEnablePwmScopeTest = false;

namespace {
void handlePwmScopeTest() {
    if (!kEnablePwmScopeTest) {
        return;
    }

    static bool initialized = false;
    static bool highDutyPhase = false;
    static unsigned long lastToggleMs = 0;

    if (!initialized) {
        pwmDebugDump();
        pwmSetDuty01(0.25f);
        lastToggleMs = millis();
        initialized = true;
        return;
    }

    unsigned long now = millis();
    if (now - lastToggleMs >= 1000UL) {
        lastToggleMs = now;
        highDutyPhase = !highDutyPhase;
        pwmSetDuty01(highDutyPhase ? 0.75f : 0.25f);
    }
}
}  // namespace

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
    handlePwmScopeTest();

    runTasks();      // Oppdater sensorer, PID, profil, failsafe
    comm.process();  // Les og behandle innkommende kommandoer fra GUI
}
