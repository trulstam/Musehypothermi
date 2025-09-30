// Musehypothermi Comm API - Stabil versjon med støtte for status-variabler
// File: comm_api.cpp

#include "comm_api.h"
#include "pid_module.h"
#include "sensor_module.h"
#include "pressure_module.h"
#include "eeprom_manager.h"
#include "task_scheduler.h"
#include "profile_manager.h"

#include <ArduinoJson.h>

extern PIDModule pid;
extern SensorModule sensors;
extern PressureModule pressure;
extern EEPROMManager eeprom;
extern ProfileManager profileManager;
extern int heartbeatTimeoutMs;

CommAPI::CommAPI(Stream &serialStream) {
    serial = &serialStream;
    buffer = "";
}

void CommAPI::begin(Stream &serialStream) {
    serial = &serialStream;
    buffer = "";

    bool resetOccurred = eeprom.begin();
    if (resetOccurred) {
        sendEvent("\u26a0\ufe0f EEPROM invalid - factory reset performed on boot");
    } else {
        sendEvent("\u2705 EEPROM validated - no reset required");
    }
}

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

void CommAPI::handleCommand(const String &jsonString) {
    StaticJsonDocument<1024> doc;
    DeserializationError error = deserializeJson(doc, jsonString);

    if (error) {
        sendResponse("JSON parse error");
        return;
    }

    if (doc.containsKey("CMD")) {
        JsonObject cmd = doc["CMD"];
        String action = cmd["action"];
        String state = cmd["state"];

        if (action == "pid") {
            if (state == "start") {
                pid.start(); sendResponse("PID started");
            } else if (state == "stop") {
                pid.stop(); sendResponse("PID stopped");
            } else if (state == "autotune") {
                pid.startAutotune(); sendResponse("Autotune started");
            } else if (state == "abort_autotune") {
                pid.abortAutotune(); sendResponse("Autotune aborted");
            } else {
                sendResponse("Unknown PID state");
            }

        } else if (action == "heartbeat") {
            heartbeatReceived(); sendResponse("heartbeat_ack");

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

        } else if (action == "profile") {
            if (state == "start") {
                profileManager.start(); sendResponse("Profile started");
            } else if (state == "pause") {
                profileManager.pause(); sendResponse("Profile paused");
            } else if (state == "resume") {
                profileManager.resume(); sendResponse("Profile resumed");
            } else if (state == "stop") {
                profileManager.stop(); sendResponse("Profile stopped");
            } else {
                sendResponse("Unknown profile state");
            }

        } else if (action == "failsafe_clear") {
            if (isFailsafeActive()) {
                clearFailsafe();
                sendResponse("Failsafe cleared");
                sendEvent("\u2705 Failsafe manually cleared via GUI");
            } else {
                sendResponse("Failsafe not active");
            }

        } else if (action == "panic") {
            triggerFailsafe("gui_panic_triggered");
            sendResponse("GUI panic triggered");

        } else if (action == "save_eeprom") {
            saveAllToEEPROM(); sendResponse("EEPROM save complete");

        } else if (action == "reset_config") {
            if (eeprom.factoryReset()) {
                sendResponse("\u2705 EEPROM reset to factory defaults");
                sendEvent("\u26a0\ufe0f EEPROM factory reset executed");
            } else {
                sendResponse("\u274c EEPROM factory reset failed");
            }

        } else {
            sendResponse("Unknown CMD action");
        }
    }

    if (doc.containsKey("SET")) {
        JsonObject set = doc["SET"];
        String variable = set["variable"];

        if (variable == "target_temp") {
            float value = set["value"];
            pid.setTargetTemp(value);
            eeprom.saveTargetTemp(value);
            sendResponse("Target temperature updated");

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

        } else if (variable == "pid_max_output") {
            float value = set["value"];
            pid.setMaxOutputPercent(value);
            eeprom.saveMaxOutput(value);
            sendResponse("Max output limit updated");

        } else if (variable == "debug_level") {
            int value = set["value"];
            pid.enableDebug(value > 0);
            eeprom.saveDebugLevel(value);
            sendResponse("Debug level updated");

        } else if (variable == "failsafe_timeout") {
            int value = set["value"];
            heartbeatTimeoutMs = value;
            eeprom.saveFailsafeTimeout(value);
            sendResponse("Failsafe timeout updated");

        } else if (variable == "profile") {
            JsonVariant value = set["value"];
            if (!value.is<JsonArray>()) {
                sendResponse("Invalid profile payload");
            } else {
                parseProfile(value.as<JsonArray>());
            }

        } else {
            sendResponse("Unknown SET variable");
        }
    }
}

void CommAPI::parseProfile(JsonArray arr) {
    const size_t profileLen = arr.size();

    if (profileLen == 0) {
        sendResponse("Profile empty");
        return;
    }

    if (profileLen > 10) {
        sendResponse("Profile too long");
        return;
    }

    ProfileManager::ProfileStep steps[10];

    for (size_t i = 0; i < profileLen; i++) {
        JsonVariant stepVariant = arr[i];
        if (!stepVariant.is<JsonObject>()) {
            sendResponse("Profile step malformed");
            return;
        }

        JsonObject step = stepVariant.as<JsonObject>();

        if (!step.containsKey("plate_start_temp") ||
            !step.containsKey("plate_end_temp") ||
            !step.containsKey("total_step_time_ms")) {
            sendResponse("Profile step missing fields");
            return;
        }

        float startTemp = step["plate_start_temp"];
        float endTemp = step["plate_end_temp"];
        uint32_t rampTime = step.containsKey("ramp_time_ms") ? step["ramp_time_ms"].as<uint32_t>() : 0;
        float rectalOverride = step.containsKey("rectal_override_target") ? step["rectal_override_target"].as<float>() : -1000.0f;
        uint32_t totalStepTime = step["total_step_time_ms"].as<uint32_t>();

        if (totalStepTime == 0) {
            sendResponse("Profile step duration invalid");
            return;
        }

        if (rampTime > totalStepTime) {
            rampTime = totalStepTime;
        }

        if (startTemp < -50.0f || startTemp > 80.0f ||
            endTemp < -50.0f || endTemp > 80.0f) {
            sendResponse("Profile temperature out of range");
            return;
        }

        steps[i].plate_start_temp = startTemp;
        steps[i].plate_end_temp = endTemp;
        steps[i].ramp_time_ms = rampTime;
        steps[i].rectal_override_target = rectalOverride;
        steps[i].total_step_time_ms = totalStepTime;
    }

    profileManager.loadProfile(steps, static_cast<uint8_t>(profileLen));
    sendResponse("Profile loaded");
}

void CommAPI::sendResponse(const String &message) {
    StaticJsonDocument<256> doc;
    doc["response"] = message;
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendEvent(const String &eventMessage) {
    StaticJsonDocument<256> doc;
    doc["event"] = eventMessage;
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendData() {
    StaticJsonDocument<1024> doc;
    doc["cooling_plate_temp"] = sensors.getCoolingPlateTemp();
    doc["anal_probe_temp"] = sensors.getRectalTemp();
    doc["pid_output"] = pid.getOutput();
    doc["breath_freq_bpm"] = pressure.getBreathRate();
    doc["failsafe"] = isFailsafeActive();
    doc["plate_target_active"] = pid.getActivePlateTarget();
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendStatus() {
    StaticJsonDocument<512> doc;
    doc["failsafe_active"] = isFailsafeActive();
    doc["failsafe_reason"] = getFailsafeReason();
    doc["cooling_plate_temp"] = sensors.getCoolingPlateTemp();
    doc["anal_probe_temp"] = sensors.getRectalTemp();
    doc["pid_output"] = pid.getOutput();
    doc["breath_freq_bpm"] = pressure.getBreathRate();
    doc["plate_target_active"] = pid.getActivePlateTarget();
    doc["profile_active"] = profileManager.isActive();
    doc["profile_paused"] = profileManager.isPaused();
    doc["profile_step"] = profileManager.getCurrentStep();
    doc["profile_remaining_time"] = profileManager.getRemainingTime();
    doc["autotune_active"] = pid.isAutotuneActive();
    doc["autotune_status"] = pid.getAutotuneStatus();
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendStatus(const char* key, float value) {
    StaticJsonDocument<128> doc;
    doc[key] = static_cast<float>(value);
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendStatus(const char* key, int value) {
    StaticJsonDocument<128> doc;
    doc[key] = value;
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendStatus(const char* key, double value) {
    StaticJsonDocument<128> doc;
    doc[key] = static_cast<float>(value);
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendPIDParams() {
    StaticJsonDocument<256> doc;
    doc["pid_kp"] = pid.getKp();
    doc["pid_ki"] = pid.getKi();
    doc["pid_kd"] = pid.getKd();
    doc["pid_max_output"] = pid.getMaxOutputPercent();
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendConfig() {
    StaticJsonDocument<512> doc;
    doc["pid_kp"] = pid.getKp();
    doc["pid_ki"] = pid.getKi();
    doc["pid_kd"] = pid.getKd();
    doc["pid_max_output"] = pid.getMaxOutputPercent();
    doc["target_temp"] = pid.getTargetTemp();
    doc["debug_level"] = pid.isDebugEnabled() ? 1 : 0;
    doc["failsafe_timeout"] = heartbeatTimeoutMs;
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::saveAllToEEPROM() {
    eeprom.savePIDParams(pid.getKp(), pid.getKi(), pid.getKd());
    eeprom.saveTargetTemp(pid.getTargetTemp());
    eeprom.saveMaxOutput(pid.getMaxOutputPercent());
    int debugLevel = pid.isDebugEnabled() ? 1 : 0;
    eeprom.saveDebugLevel(debugLevel);
    eeprom.saveFailsafeTimeout(heartbeatTimeoutMs);
}
