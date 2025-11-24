// Musehypothermi Task Scheduler - TRÅD 5 + JSON Event Edition
// File: task_scheduler.cpp

#include "task_scheduler.h"
#include "pid_module_asymmetric.h"  // Changed from pid_module.h
#include "sensor_module.h"
#include "pressure_module.h"
#include "profile_manager.h"
#include "eeprom_manager.h"
#include "comm_api.h"

#include <string.h>

#include "arduino_platform.h"

// === Eksterne moduler ===
extern AsymmetricPIDModule pid;  // Changed from PIDModule
extern SensorModule sensors;
extern PressureModule pressure;
extern ProfileManager profileManager;
extern EEPROMManager eeprom;
extern CommAPI comm;  // Brukes til sendEvent()

// === Failsafe status ===
static bool failsafeActive = false;
static const char* failsafeReason = "";
static bool breathCheckEnabled = true;

// === Panic status ===
static bool panicActive = false;
static const char* panicReason = "";

// === Heartbeat monitor ===
unsigned long lastHeartbeatMillis = 0;

// === Failsafe parametre (oppdatert fra EEPROM i initTasks) ===
int heartbeatTimeoutMs = 5000;  // default, lastes i initTasks
int breathingTimeoutMs = 10000; // kan lastes fra EEPROM senere

// === Panic Button ===
// No physical panic input is wired right now; keep it disabled with -1 so
// nothing can trigger panic from a floating pin. If you move the button to a
// free GPIO (pin 7 is already used by the PID direction output), set the pin
// number here: it will be configured with INPUT_PULLUP in initTasks() and a
// LOW level will trigger panic in checkPanicButton().
static constexpr int PANIC_BUTTON_PIN = -1;

// === Trigger failsafe ===
void triggerFailsafe(const char* reason) {
    if (panicActive) {
        return;
    }

    if (!failsafeActive) {
        failsafeActive = true;
        failsafeReason = reason;

        pid.enterFailsafeState();
        profileManager.abortDueToSafety("failsafe");

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

void setBreathCheckEnabled(bool enabled) {
    breathCheckEnabled = enabled;

    if (!breathCheckEnabled && failsafeActive &&
        strcmp(failsafeReason, "no_breathing_detected") == 0) {
        clearFailsafe();
        comm.sendEvent("✅ Breath-stop failsafe cleared (check disabled)");
    }
}

bool isBreathCheckEnabled() {
    return breathCheckEnabled;
}

void triggerPanic(const char* reason) {
    if (panicActive) {
        return;
    }

    panicActive = true;
    panicReason = reason ? reason : "panic_triggered";
    clearFailsafe();

    pid.enterPanicState();
    profileManager.abortDueToSafety("panic");

    String msg = "🚨 PANIC TRIGGERED: ";
    msg += panicReason;
    comm.sendEvent(msg);
}

void clearPanic() {
    panicActive = false;
    panicReason = "";
    pid.ensureOutputsOff();
}

bool isPanicActive() {
    return panicActive;
}

const char* getPanicReason() {
    return panicReason;
}

// === Heartbeat received ===
void heartbeatReceived() {
    lastHeartbeatMillis = millis();

    // Automatisk clear hvis failsafe skyldes heartbeat_timeout
    if (isFailsafeActive() && strcmp(getFailsafeReason(), "heartbeat_timeout") == 0) {
        clearFailsafe();
        comm.sendEvent("✅ Failsafe cleared after heartbeat recovery");
    }
}

// === Task timers ===
static unsigned long lastSensorUpdate = 0;
static unsigned long lastPIDUpdate = 0;
static unsigned long lastPressureUpdate = 0;
static unsigned long lastProfileUpdate = 0;

// === Init Tasks ===
void initTasks() {
    if (PANIC_BUTTON_PIN >= 0) {
        pinMode(PANIC_BUTTON_PIN, INPUT_PULLUP);  // Kan aktiveres hvis fysisk knapp kobles
    }
    clearFailsafe();

    eeprom.loadFailsafeTimeout(heartbeatTimeoutMs);

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

// === Check panic button (deaktivert – pin ikke koblet) ===
void checkPanicButton() {
    // Deaktivert fordi pin 7 ikke er koblet til fysisk knapp.
    // Hvis du kobler opp en knapp senere, fjern kommentaren under:
    /*
    if (digitalRead(PANIC_BUTTON_PIN) == LOW) {
        triggerFailsafe("panic_button_triggered");
    }
    */
}

// === Run tasks ===
void runTasks() {
    unsigned long now = millis();

    // === Check panic button ===
    // checkPanicButton();  // Deaktivert inntil fysisk knapp er koblet

    // === Heartbeat timeout ===
    if (now - lastHeartbeatMillis > (unsigned long)heartbeatTimeoutMs) {
        triggerFailsafe("heartbeat_timeout");
    }

    // === Panic overrides everything ===
    if (isPanicActive()) {
        pid.enterPanicState();
        profileManager.abortDueToSafety("panic");
        return;
    }

    // === If failsafe active, skip remaining tasks ===
    if (isFailsafeActive()) {
        pid.enterFailsafeState();
        profileManager.abortDueToSafety("failsafe");
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

        if (breathCheckEnabled && pressure.getBreathRate() < 1.0) {
            triggerFailsafe("no_breathing_detected");
        }
    }

    // === PID / AUTOTUNE UPDATE ===
    if (now - lastPIDUpdate >= 100) {
        if (pid.isAutotuneActive()) {
            pid.runAsymmetricAutotune();  // Changed from runAutotune()
        } else if (pid.isEquilibriumEstimating()) {
            pid.updateEquilibriumEstimationTask();
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