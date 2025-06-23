// Musehypothermi Task Scheduler - TRÅD 5 + JSON Event Edition
// File: task_scheduler.cpp

#include "task_scheduler.h"
#include "pid_module.h"
#include "sensor_module.h"
#include "pressure_module.h"
#include "profile_manager.h"
#include "eeprom_manager.h"
#include "comm_api.h"

#include <Arduino.h>

// === Eksterne moduler ===
extern PIDModule pid;
extern SensorModule sensors;
extern PressureModule pressure;
extern ProfileManager profileManager;
extern EEPROMManager eeprom;
extern CommAPI comm;  // Brukes til sendEvent()

// === Failsafe status ===
static bool failsafeActive = false;
static const char* failsafeReason = "";

// === Heartbeat monitor ===
unsigned long lastHeartbeatMillis = 0;

// === Failsafe parametre (oppdatert fra EEPROM i initTasks) ===
int heartbeatTimeoutMs = 5000;  // default, lastes i initTasks
int breathingTimeoutMs = 10000; // kan lastes fra EEPROM senere

// === Panic Button ===
#define PANIC_BUTTON_PIN 7

// === Trigger failsafe ===
void triggerFailsafe(const char* reason) {
    if (!failsafeActive) {
        failsafeActive = true;
        failsafeReason = reason;

        if (pid.isAutotuneActive()) {
            pid.abortAutotune();
        }

        pid.stop();
        profileManager.stop();

        String msg = "⚠️ FAILSAFE TRIGGERED: ";
        msg += reason;
        comm.sendEvent(msg);
    }
}

void clearFailsafe() {
    failsafeActive = false;
    failsafeReason = "";
}

bool isFailsafeActive() {
    return failsafeActive;
}

const char* getFailsafeReason() {
    return failsafeReason;
}

// === Heartbeat received ===
void heartbeatReceived() {
    lastHeartbeatMillis = millis();
}

// === Task timers ===
static unsigned long lastSensorUpdate = 0;
static unsigned long lastPIDUpdate = 0;
static unsigned long lastPressureUpdate = 0;
static unsigned long lastProfileUpdate = 0;

// === Init Tasks ===
void initTasks() {
    pinMode(PANIC_BUTTON_PIN, INPUT_PULLUP);
    clearFailsafe();

    // Last parametre fra EEPROM
    eeprom.loadFailsafeTimeout(heartbeatTimeoutMs);
    // breathingTimeoutMs kan lastes senere hvis ønskelig

    String msg = "✅ initTasks complete. HeartbeatTimeout: ";
    msg += String(heartbeatTimeoutMs) + " ms";
    comm.sendEvent(msg);

    unsigned long now = millis();
    lastSensorUpdate = now;
    lastPIDUpdate = now;
    lastPressureUpdate = now;
    lastProfileUpdate = now;
    lastHeartbeatMillis = now;
}

// === Check panic button ===
void checkPanicButton() {
    if (digitalRead(PANIC_BUTTON_PIN) == LOW) {
        triggerFailsafe("panic_button_triggered");
    }
}

// === Run tasks ===
void runTasks() {
    unsigned long now = millis();

    // === Check panic button ===
    checkPanicButton();

    // === Heartbeat timeout ===
    if (now - lastHeartbeatMillis > (unsigned long)heartbeatTimeoutMs) {
        triggerFailsafe("heartbeat_timeout");
    }

    // === If failsafe active, skip remaining tasks ===
    if (isFailsafeActive()) {
        return;
    }

    // === SENSOR UPDATE (Temp probes) ===
    if (now - lastSensorUpdate >= 100) {
        sensors.update();
        lastSensorUpdate = now;
    }

    // === PRESSURE UPDATE (Breathing monitor) ===
    if (now - lastPressureUpdate >= 100) {
        pressure.update();
        lastPressureUpdate = now;

        if (pressure.getBreathRate() < 1.0) {
            triggerFailsafe("no_breathing_detected");
        }
    }

    // === PID / AUTOTUNE UPDATE ===
    if (now - lastPIDUpdate >= 100) {
        if (pid.isAutotuneActive()) {
            pid.runAutotune();
        } else if (pid.isActive()) {
            pid.update(sensors.getRectalTemp());
        }

        lastPIDUpdate = now;
    }

    // === PROFILE UPDATE ===
    if (now - lastProfileUpdate >= 100) {
        profileManager.update();
        lastProfileUpdate = now;
    }

    // === Optional debug ===
    #ifdef DEBUG_TASKS
    static unsigned long debugPrintMillis = 0;
    if (now - debugPrintMillis >= 5000) {
        comm.sendEvent("[DEBUG] runTasks active, no failsafe");
        debugPrintMillis = now;
    }
    #endif
}
