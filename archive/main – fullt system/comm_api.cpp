// Musehypothermi Comm API - Final TRÅD 5 + Factory Reset Edition
// File: comm_api.cpp

#include "comm_api.h"
#include "pid_module.h"
#include "sensor_module.h"
#include "pressure_module.h"
#include "eeprom_manager.h"
#include "task_scheduler.h"
#include "profile_manager.h"

#include <ArduinoJson.h>

// === Eksterne instanser ===
extern PIDModule pid;
extern SensorModule sensors;
extern PressureModule pressure;
extern EEPROMManager eeprom;
extern ProfileManager profileManager;

// === Failsafe-timer (hentes fra EEPROM ved initTasks)
extern int heartbeatTimeoutMs;  // deklarert i task_scheduler.cpp

// === Constructor / init ===
CommAPI::CommAPI(Stream &serialStream) {
    serial = &serialStream;
    buffer = "";
}

void CommAPI::begin(Stream &serialStream, bool factoryResetOccurred) {
    serial = &serialStream;
    buffer = "";

    if (factoryResetOccurred) {
        sendEvent("🚨 EEPROM invalid - factory reset performed on boot");
    } else {
        sendEvent("✅ EEPROM validated - no reset required");
    }
}

// === Process incoming serial ===
void CommAPI::process() {
    while (serial->available()) {
        char c = serial->read();
        if (c == '\n') {
            handleCommand(buffer);
            buffer = "";
        } else {
            buffer += c;
        }
    }
}

// === Handle incoming JSON ===
void CommAPI::handleCommand(const String &jsonString) {
    StaticJsonDocument<1024> doc;
    DeserializationError error = deserializeJson(doc, jsonString);

    if (error) {
        sendResponse("JSON parse error");
        return;
    }

    // === CMD ===
    if (doc.containsKey("CMD")) {
        JsonObject cmd = doc["CMD"];
        String action = cmd["action"];
        String state = cmd["state"];

        // === PID actions ===
        if (action == "pid") {
            if (state == "start") {
                pid.start();
                sendResponse("PID started");
            } else if (state == "stop") {
                pid.stop();
                sendResponse("PID stopped");
            } else if (state == "autotune") {
                pid.startAutotune();
                sendResponse("Autotune started");
            } else if (state == "abort_autotune") {
                pid.abortAutotune();
                sendResponse("Autotune aborted");
            } else {
                sendResponse("Unknown PID state");
            }

        // === Heartbeat ===
        } else if (action == "heartbeat") {
            heartbeatReceived();
            sendResponse("heartbeat_ack");

        // === Get commands ===
        } else if (action == "get") {
            if (state == "pid_params") {
                sendPIDParams();
            } else if (state == "data") {
                sendData();
            } else if (state == "status") {
                sendStatus();
            } else if (state == "config") {
                sendConfig();
            } else {
                sendResponse("Unknown GET action");
            }

        // === Profile controls ===
        } else if (action == "profile") {
            if (state == "start") {
                profileManager.start();
                sendResponse("Profile started");
            } else if (state == "pause") {
                profileManager.pause();
                sendResponse("Profile paused");
            } else if (state == "resume") {
                profileManager.resume();
                sendResponse("Profile resumed");
            } else if (state == "stop") {
                profileManager.stop();
                sendResponse("Profile stopped");
            } else {
                sendResponse("Unknown profile state");
            }

        // === Failsafe clear ===
        } else if (action == "failsafe_clear") {
            clearFailsafe();
            sendResponse("Failsafe cleared");

        // === Panic trigger ===
        } else if (action == "panic") {
            triggerFailsafe("gui_panic_triggered");
            sendResponse("GUI panic triggered");

        // === Save config to EEPROM ===
        } else if (action == "save_eeprom") {
            saveAllToEEPROM();
            sendResponse("EEPROM save complete");

        // === Factory Reset via CMD ===
        } else if (action == "reset_config") {
            if (eeprom.factoryReset()) {
                sendResponse("✅ EEPROM reset to factory defaults");
                sendEvent("⚠️ EEPROM factory reset executed");
            } else {
                sendResponse("❌ EEPROM factory reset failed");
            }

        } else {
            sendResponse("Unknown CMD action");
        }
    }

    // === SET ===
    if (doc.containsKey("SET")) {
        JsonObject set = doc["SET"];
        String variable = set["variable"];

        // === Target temperature ===
        if (variable == "target_temp") {
            float value = set["value"];
            pid.setTargetTemp(value);
            eeprom.saveTargetTemp(value);
            sendResponse("Target temperature updated");

        // === PID params ===
        } else if (variable == "pid_kp") {
            float value = set["value"];
            pid.setKp(value);
            eeprom.savePIDParams(pid.getKp(), pid.getKi(), pid.getKd());
            sendResponse("Kp updated");

        } else if (variable == "pid_ki") {
            float value = set["value"];
            pid.setKi(value);
            eeprom.savePIDParams(pid.getKp(), pid.getKi(), pid.getKd());
            sendResponse("Ki updated");

        } else if (variable == "pid_kd") {
            float value = set["value"];
            pid.setKd(value);
            eeprom.savePIDParams(pid.getKp(), pid.getKi(), pid.getKd());
            sendResponse("Kd updated");

        // === Max Output ===
        } else if (variable == "pid_max_output") {
            float value = set["value"];
            pid.setMaxOutputPercent(value);
            eeprom.saveMaxOutput(value);
            sendResponse("Max output limit updated");

        // === Debug level
        } else if (variable == "debug_level") {
            int value = set["value"];
            pid.enableDebug(value > 0);
            eeprom.saveDebugLevel(value);
            sendResponse("Debug level updated");

        // === Failsafe timeout
        } else if (variable == "failsafe_timeout") {
            int value = set["value"];
            heartbeatTimeoutMs = value;
            eeprom.saveFailsafeTimeout(value);
            sendResponse("Failsafe timeout updated");

        // === Profile ===
        } else if (variable == "profile") {
            JsonArray profileArray = set["value"].as<JsonArray>();
            parseProfile(profileArray);

        } else {
            sendResponse("Unknown SET variable");
        }
    }
}

// === Profile parsing ===
void CommAPI::parseProfile(JsonArray arr) {
    const int profileLen = arr.size();

    if (profileLen == 0 || profileLen > 10) {
        sendResponse("Invalid profile length");
        return;
    }

    ProfileManager::ProfileStep steps[10];
    for (int i = 0; i < profileLen; i++) {
        float startTemp = arr[i]["plate_start_temp"] | -100;
        float endTemp = arr[i]["plate_end_temp"] | -100;
        uint32_t rampTime = arr[i]["ramp_time_ms"] | 0;
        float rectalOverride = arr[i]["rectal_override_target"] | -1000;
        uint32_t totalStepTime = arr[i]["total_step_time_ms"] | 0;

        if (startTemp < -50 || endTemp < -50 || rampTime == 0 || totalStepTime == 0) {
            sendResponse("Invalid profile step");
            return;
        }

        steps[i].plate_start_temp = startTemp;
        steps[i].plate_end_temp = endTemp;
        steps[i].ramp_time_ms = rampTime;
        steps[i].rectal_override_target = rectalOverride;
        steps[i].total_step_time_ms = totalStepTime;
    }

    profileManager.loadProfile(steps, profileLen);
    sendResponse("Profile loaded");
}

// === Response helper ===
void CommAPI::sendResponse(const String &message) {
    StaticJsonDocument<256> doc;
    doc["response"] = message;
    serializeJson(doc, *serial);
    serial->println();
}

// === Event helper ===
void CommAPI::sendEvent(const String &eventMessage) {
    StaticJsonDocument<256> doc;
    doc["event"] = eventMessage;
    serializeJson(doc, *serial);
    serial->println();
}

// === Data sending ===
void CommAPI::sendData() {
    StaticJsonDocument<1024> doc;

    doc["cooling_plate_temp"] = sensors.getCoolingPlateTemp();
    doc["anal_probe_temp"]    = sensors.getRectalTemp();
    doc["pid_output"]         = pid.getOutput();
    doc["breath_freq_bpm"]    = pressure.getBreathRate();
    doc["failsafe"]           = isFailsafeActive();

    serializeJson(doc, *serial);
    serial->println();
}

// === Status sending ===
void CommAPI::sendStatus() {
    StaticJsonDocument<512> doc;

    doc["failsafe_active"] = isFailsafeActive();
    doc["failsafe_reason"] = getFailsafeReason();

    doc["cooling_plate_temp"] = sensors.getCoolingPlateTemp();
    doc["anal_probe_temp"]    = sensors.getRectalTemp();
    doc["pid_output"]         = pid.getOutput();
    doc["breath_freq_bpm"]    = pressure.getBreathRate();

    doc["profile_active"] = profileManager.isActive();
    doc["profile_paused"] = profileManager.isPaused();
    doc["profile_step"]   = profileManager.getCurrentStep();
    doc["profile_remaining_time"] = profileManager.getRemainingTime();

    doc["autotune_active"]  = pid.isAutotuneActive();
    doc["autotune_status"]  = pid.getAutotuneStatus();
    doc["autotune_phase"]   = pid.getAutotunePhase();
    doc["autotune_progress"] = pid.getAutotuneProgress();

    doc["pid_kp"] = pid.getKp();
    doc["pid_ki"] = pid.getKi();
    doc["pid_kd"] = pid.getKd();
    doc["pid_max_output"] = pid.getMaxOutputPercent();

    serializeJson(doc, *serial);
    serial->println();
}

// === PID param sending ===
void CommAPI::sendPIDParams() {
    StaticJsonDocument<256> doc;

    doc["pid_kp"]         = pid.getKp();
    doc["pid_ki"]         = pid.getKi();
    doc["pid_kd"]         = pid.getKd();
    doc["pid_max_output"] = pid.getMaxOutputPercent();

    serializeJson(doc, *serial);
    serial->println();
}

// === Config sending (full config snapshot) ===
void CommAPI::sendConfig() {
    StaticJsonDocument<512> doc;

    doc["pid_kp"]         = pid.getKp();
    doc["pid_ki"]         = pid.getKi();
    doc["pid_kd"]         = pid.getKd();
    doc["pid_max_output"] = pid.getMaxOutputPercent();
    doc["target_temp"]    = pid.getTargetTemp();
    doc["debug_level"]    = pid.isDebugEnabled() ? 1 : 0;
    doc["failsafe_timeout"] = heartbeatTimeoutMs;

    serializeJson(doc, *serial);
    serial->println();
}

// === EEPROM bulk save ===
void CommAPI::saveAllToEEPROM() {
    eeprom.savePIDParams(pid.getKp(), pid.getKi(), pid.getKd());
    eeprom.saveTargetTemp(pid.getTargetTemp());
    eeprom.saveMaxOutput(pid.getMaxOutputPercent());
    int debugLevel = pid.isDebugEnabled() ? 1 : 0;
    eeprom.saveDebugLevel(debugLevel);
    eeprom.saveFailsafeTimeout(heartbeatTimeoutMs);
}
