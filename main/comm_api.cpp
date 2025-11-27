// Musehypothermi Comm API - Recovery-style minimal command set
// File: comm_api.cpp

#include "comm_api.h"
#include "pid_module.h"
#include "sensor_module.h"
#include "pressure_module.h"
#include "eeprom_manager.h"
#include "task_scheduler.h"
#include "profile_manager.h"

#include <ArduinoJson.h>
#include <string.h>

extern PIDModule pid;
extern SensorModule sensors;
extern PressureModule pressure;
extern EEPROMManager eeprom;
extern ProfileManager profileManager;
extern int heartbeatTimeoutMs;

namespace {
// Keep the large command document out of the stack to avoid exhausting RAM
// during parsing of large payloads such as profile uploads.
static StaticJsonDocument<3072> commandDoc;
}  // namespace

CommAPI::CommAPI(Stream &serialStream) {
    serial = &serialStream;
    buffer = "";
}

void CommAPI::begin(Stream &serialStream, bool factoryResetOccurred) {
    serial = &serialStream;
    buffer = "";

    if (factoryResetOccurred) {
        sendEvent("\u26a0\ufe0f EEPROM factory reset detected at boot");
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
    commandDoc.clear();
    DeserializationError error = deserializeJson(commandDoc, jsonString);

    if (error) {
        sendResponse("JSON parse error");
        return;
    }

    if (commandDoc.containsKey("CMD")) {
        JsonObject cmd = commandDoc["CMD"];
        String action = cmd["action"];
        String state = cmd["state"];

        if (action == "pid") {
            if (state == "start") {
                bool started = pid.start();
                sendResponse(started ? "PID started" : "PID blocked: panic/failsafe active");
            } else if (state == "stop") {
                pid.stop();
                sendResponse("PID stopped");
            } else {
                sendResponse("unsupported_command");
            }

        } else if (action == "heartbeat") {
            heartbeatReceived();
            sendResponse("heartbeat_ack");

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
                sendResponse("unsupported_command");
            }

        } else if (action == "profile") {
            if (state == "start") {
                if (profileManager.start()) {
                    sendResponse("Profile started");
                    sendEvent("Profile started");
                } else {
                    sendResponse("Profile blocked");
                }
            } else if (state == "pause") {
                profileManager.pause();
                sendResponse("Profile paused");
                sendEvent("Profile paused");
            } else if (state == "resume") {
                profileManager.resume();
                sendResponse("Profile resumed");
                sendEvent("Profile resumed");
            } else if (state == "stop") {
                profileManager.stop();
                sendResponse("Profile stopped");
                sendEvent("Profile stopped");
            } else {
                sendResponse("unsupported_command");
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
            triggerPanic("gui_panic_triggered");
            sendEvent("Panic triggered: gui_panic_triggered");
            sendResponse("GUI panic triggered");

        } else if (action == "save_eeprom") {
            saveAllToEEPROM();
            sendResponse("EEPROM save complete");

        } else if (action == "reset_config") {
            if (eeprom.factoryReset()) {
                sendResponse("\u2705 EEPROM reset to factory defaults");
                sendEvent("\u26a0\ufe0f EEPROM factory reset executed");
            } else {
                sendResponse("\u274c EEPROM factory reset failed");
            }
        } else {
            sendResponse("unsupported_command");
        }
    }

    if (commandDoc.containsKey("SET")) {
        JsonObject set = commandDoc["SET"];
        if (!set.containsKey("variable")) {
            sendResponse("unsupported_command");
            return;
        }

        String variable = set["variable"];

        if (variable == "target_temp") {
            float value = set["value"];
            pid.setTargetTemp(value);
            eeprom.saveTargetTemp(value);
            sendResponse("Target temperature updated");

        } else if (variable == "pid_kp") {
            float value = set["value"];
            pid.setHeatingPID(value, pid.getHeatingKi(), pid.getHeatingKd());
            sendResponse("Heating Kp updated");

        } else if (variable == "pid_ki") {
            float value = set["value"];
            pid.setHeatingPID(pid.getHeatingKp(), value, pid.getHeatingKd());
            sendResponse("Heating Ki updated");

        } else if (variable == "pid_kd") {
            float value = set["value"];
            pid.setHeatingPID(pid.getHeatingKp(), pid.getHeatingKi(), value);
            sendResponse("Heating Kd updated");

        } else if (variable == "pid_max_output") {
            float value = set["value"];
            pid.setMaxOutputPercent(value);
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

        } else if (variable == "profile_data") {
            JsonVariant value = set["value"];
            if (!value.is<JsonArray>()) {
                sendResponse("Invalid profile payload");
            } else {
                parseProfile(value.as<JsonArray>());
            }

        } else {
            sendResponse("unsupported_command");
        }
    }
}

void CommAPI::parseProfile(JsonArray arr) {
    const size_t profileLen = arr.size();

    if (profileLen == 0) {
        sendResponse("Profile empty");
        return;
    }

    if (profileLen > ProfileManager::MAX_STEPS) {
        sendResponse("Profile too long");
        return;
    }

    ProfileManager::ProfileStep steps[ProfileManager::MAX_STEPS];
    size_t loadedSteps = 0;
    uint32_t lastTime = 0;

    for (size_t i = 0; i < profileLen && loadedSteps < ProfileManager::MAX_STEPS; i++) {
        JsonVariant stepVariant = arr[i];
        if (!stepVariant.is<JsonObject>()) {
            sendResponse("Profile step malformed");
            return;
        }

        JsonObject step = stepVariant.as<JsonObject>();

        if (!step.containsKey("t") || (!step.containsKey("temp") && !step.containsKey("plate_target"))) {
            sendResponse("Profile step missing fields");
            return;
        }

        float targetTemp = step.containsKey("temp") ? step["temp"].as<float>() : step["plate_target"].as<float>();
        uint32_t timeMs = static_cast<uint32_t>(step["t"].as<float>() * 1000.0f);

        if (timeMs < lastTime) {
            sendResponse("Profile time not ascending");
            return;
        }

        steps[loadedSteps].time_ms = timeMs;
        steps[loadedSteps].plate_target = targetTemp;
        lastTime = timeMs;
        loadedSteps++;
    }

    if (loadedSteps == 0) {
        sendResponse("No valid profile steps");
        return;
    }

    if (!profileManager.loadProfile(steps, static_cast<uint8_t>(loadedSteps))) {
        sendResponse("Profile rejected");
        return;
    }

    sendResponse("Profile loaded");
}

void CommAPI::sendResponse(const String &message) {
    static StaticJsonDocument<256> doc;
    doc.clear();
    doc["response"] = message;
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendEvent(const String &eventMessage) {
    static StaticJsonDocument<256> doc;
    doc.clear();
    doc["event"] = eventMessage;
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendPIDParams() {
    static StaticJsonDocument<256> doc;
    doc.clear();
    doc["pid_kp"] = pid.getHeatingKp();
    doc["pid_ki"] = pid.getHeatingKi();
    doc["pid_kd"] = pid.getHeatingKd();
    doc["pid_heating_kp"] = pid.getHeatingKp();
    doc["pid_heating_ki"] = pid.getHeatingKi();
    doc["pid_heating_kd"] = pid.getHeatingKd();
    doc["pid_cooling_kp"] = pid.getCoolingKp();
    doc["pid_cooling_ki"] = pid.getCoolingKi();
    doc["pid_cooling_kd"] = pid.getCoolingKd();
    doc["pid_max_output"] = pid.getMaxOutputPercent();
    doc["pid_heating_limit"] = pid.getHeatingOutputLimit();
    doc["pid_cooling_limit"] = pid.getCoolingOutputLimit();
    doc["pid_mode"] = pid.isCooling() ? "cooling" : "heating";
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendData() {
    static StaticJsonDocument<1024> doc;
    doc.clear();
    doc["cooling_plate_temp"] = sensors.getCoolingPlateTemp();
    doc["anal_probe_temp"] = sensors.getRectalTemp();
    doc["pid_output"] = pid.getOutput();
    doc["breath_freq_bpm"] = pressure.getBreathRate();
    doc["failsafe_active"] = isFailsafeActive();
    doc["failsafe_reason"] = getFailsafeReason();
    doc["breath_check_enabled"] = isBreathCheckEnabled();
    doc["panic_active"] = isPanicActive();
    doc["panic_reason"] = getPanicReason();
    doc["plate_target_active"] = pid.getActivePlateTarget();
    doc["cooling_mode"] = pid.isCooling();
    doc["temperature_rate"] = pid.getTemperatureRate();
    doc["pid_max_output"] = pid.getMaxOutputPercent();
    doc["pid_heating_limit"] = pid.getHeatingOutputLimit();
    doc["pid_cooling_limit"] = pid.getCoolingOutputLimit();
    doc["pid_heating_kp"] = pid.getHeatingKp();
    doc["pid_heating_ki"] = pid.getHeatingKi();
    doc["pid_heating_kd"] = pid.getHeatingKd();
    doc["pid_cooling_kp"] = pid.getCoolingKp();
    doc["pid_cooling_ki"] = pid.getCoolingKi();
    doc["pid_cooling_kd"] = pid.getCoolingKd();
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendStatus() {
    static StaticJsonDocument<768> doc;
    doc.clear();
    doc["failsafe_active"] = isFailsafeActive();
    doc["failsafe_reason"] = getFailsafeReason();
    doc["breath_check_enabled"] = isBreathCheckEnabled();
    doc["panic_active"] = isPanicActive();
    doc["panic_reason"] = getPanicReason();
    double plateTemp = sensors.getCoolingPlateTemp();
    double rectalTemp = sensors.getRectalTemp();

    doc["cooling_plate_temp"] = plateTemp;
    doc["rectal_temp"] = rectalTemp;
    doc["anal_probe_temp"] = rectalTemp;

    double plateRaw = sensors.getCoolingPlateRawTemp();
    double rectalRaw = sensors.getRectalRawTemp();
    doc["cooling_plate_raw"] = plateRaw;
    doc["rectal_raw"] = rectalRaw;
    doc["cooling_plate_temp_raw"] = plateRaw;
    doc["anal_probe_temp_raw"] = rectalRaw;
    doc["pid_output"] = pid.getOutput();
    doc["breath_freq_bpm"] = pressure.getBreathRate();
    doc["plate_target_active"] = pid.getActivePlateTarget();
    doc["profile_active"] = profileManager.isActive();
    doc["profile_paused"] = profileManager.isPaused();
    doc["profile_step_index"] = profileManager.getCurrentStep();
    doc["profile_remaining_time"] = profileManager.getRemainingTime();
    doc["cooling_mode"] = pid.isCooling();
    doc["pid_mode"] = pid.isCooling() ? "cooling" : "heating";
    doc["emergency_stop"] = pid.isEmergencyStop();
    doc["temperature_rate"] = pid.getTemperatureRate();
    doc["pid_max_output"] = pid.getMaxOutputPercent();
    doc["pid_heating_limit"] = pid.getHeatingOutputLimit();
    doc["pid_cooling_limit"] = pid.getCoolingOutputLimit();
    doc["pid_heating_kp"] = pid.getHeatingKp();
    doc["pid_heating_ki"] = pid.getHeatingKi();
    doc["pid_heating_kd"] = pid.getHeatingKd();
    doc["pid_cooling_kp"] = pid.getCoolingKp();
    doc["pid_cooling_ki"] = pid.getCoolingKi();
    doc["pid_cooling_kd"] = pid.getCoolingKd();
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendStatus(const char* key, float value) {
    static StaticJsonDocument<128> doc;
    doc.clear();
    doc[key] = static_cast<float>(value);
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendStatus(const char* key, int value) {
    static StaticJsonDocument<128> doc;
    doc.clear();
    doc[key] = static_cast<int>(value);
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendStatus(const char* key, double value) {
    static StaticJsonDocument<128> doc;
    doc.clear();
    doc[key] = static_cast<double>(value);
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendConfig() {
    static StaticJsonDocument<512> doc;
    doc.clear();
    doc["pid_kp"] = pid.getHeatingKp();
    doc["pid_ki"] = pid.getHeatingKi();
    doc["pid_kd"] = pid.getHeatingKd();
    doc["pid_heating_kp"] = pid.getHeatingKp();
    doc["pid_heating_ki"] = pid.getHeatingKi();
    doc["pid_heating_kd"] = pid.getHeatingKd();
    doc["pid_cooling_kp"] = pid.getCoolingKp();
    doc["pid_cooling_ki"] = pid.getCoolingKi();
    doc["pid_cooling_kd"] = pid.getCoolingKd();
    doc["pid_max_output"] = pid.getMaxOutputPercent();
    doc["pid_heating_limit"] = pid.getHeatingOutputLimit();
    doc["pid_cooling_limit"] = pid.getCoolingOutputLimit();
    doc["target_temp"] = pid.getTargetTemp();
    doc["debug_level"] = pid.isDebugEnabled() ? 1 : 0;
    doc["failsafe_timeout"] = heartbeatTimeoutMs;
    doc["breath_check_enabled"] = isBreathCheckEnabled();
    doc["cooling_rate_limit"] = pid.getCoolingRateLimit();
    doc["deadband"] = pid.getCurrentDeadband();
    doc["safety_margin"] = pid.getSafetyMargin();
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::saveAllToEEPROM() {
    eeprom.saveHeatingPIDParams(pid.getHeatingKp(), pid.getHeatingKi(), pid.getHeatingKd());
    eeprom.saveCoolingPIDParams(pid.getCoolingKp(), pid.getCoolingKi(), pid.getCoolingKd());
    eeprom.saveTargetTemp(pid.getTargetTemp());

    EEPROMManager::OutputLimits limits{
        pid.getHeatingOutputLimit(),
        pid.getCoolingOutputLimit(),
    };
    eeprom.saveOutputLimits(limits);

    EEPROMManager::SafetySettings safety{
        pid.getCoolingRateLimit(),
        pid.getCurrentDeadband(),
        pid.getSafetyMargin(),
    };
    eeprom.saveSafetySettings(safety);

    eeprom.saveMaxOutput(pid.getMaxOutputPercent());
    eeprom.saveDebugLevel(pid.isDebugEnabled() ? 1 : 0);
    eeprom.saveFailsafeTimeout(heartbeatTimeoutMs);
}
