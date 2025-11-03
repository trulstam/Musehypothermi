// Musehypothermi Comm API - Stabil versjon med støtte for status-variabler
// File: comm_api.cpp

#include "comm_api.h"
#include "pid_module_asymmetric.h"  // CHANGED: was "pid_module.h"
#include "sensor_module.h"
#include "pressure_module.h"
#include "eeprom_manager.h"
#include "task_scheduler.h"
#include "profile_manager.h"

#include <ArduinoJson.h>

extern AsymmetricPIDModule pid;  // CHANGED: was PIDModule pid;
extern SensorModule sensors;
extern PressureModule pressure;
extern EEPROMManager eeprom;
extern ProfileManager profileManager;
extern int heartbeatTimeoutMs;

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
    // The profile upload payload can easily exceed 1 KB when 10 steps are
    // transferred. A too-small document caused the JSON deserialisation to
    // fail silently, which meant the controller never received the profile
    // (and thus ignored subsequent start commands). Allocate a larger buffer
    // so we can parse complete profile uploads without errors.
    StaticJsonDocument<3072> doc;
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
        } else if (action == "set_cooling_pid") {
            JsonObject params = cmd["params"];
            if (!params.isNull() && params.containsKey("kp") &&
                params.containsKey("ki") && params.containsKey("kd")) {
                float kp = params["kp"];
                float ki = params["ki"];
                float kd = params["kd"];
                pid.setCoolingPID(kp, ki, kd);
                String message = "🧊 Cooling PID via GUI (kp=";
                message += String(kp, 4);
                message += ", ki=";
                message += String(ki, 4);
                message += ", kd=";
                message += String(kd, 4);
                message += ")";
                sendEvent(message);
                sendResponse("Cooling PID updated");
            } else {
                sendResponse("Cooling PID parameters missing");
            }

        } else if (action == "set_heating_pid") {
            JsonObject params = cmd["params"];
            if (!params.isNull() && params.containsKey("kp") &&
                params.containsKey("ki") && params.containsKey("kd")) {
                float kp = params["kp"];
                float ki = params["ki"];
                float kd = params["kd"];
                pid.setHeatingPID(kp, ki, kd);
                String message = "🔥 Heating PID via GUI (kp=";
                message += String(kp, 4);
                message += ", ki=";
                message += String(ki, 4);
                message += ", kd=";
                message += String(kd, 4);
                message += ")";
                sendEvent(message);
                sendResponse("Heating PID updated");
            } else {
                sendResponse("Heating PID parameters missing");
            }

        } else if (action == "emergency_stop") {
            JsonObject params = cmd["params"];
            bool enabled = true;
            if (!params.isNull() && params.containsKey("enabled")) {
                enabled = params["enabled"];
            }
            pid.setEmergencyStop(enabled);
            sendResponse(enabled ? "Emergency stop enabled" : "Emergency stop cleared");

        } else if (action == "set_cooling_rate_limit") {
            JsonObject params = cmd["params"];
            if (!params.isNull() && params.containsKey("rate")) {
                float rate = params["rate"];
                pid.setCoolingRateLimit(rate);
                sendResponse("Cooling rate limit updated");
            } else {
                sendResponse("Cooling rate limit missing");
            }

        } else if (action == "set_safety_margin") {
            JsonObject params = cmd["params"];
            if (!params.isNull() && (params.containsKey("margin") || params.containsKey("deadband"))) {
                float margin = params.containsKey("margin") ? params["margin"].as<float>() : pid.getSafetyMargin();
                float deadband = params.containsKey("deadband") ? params["deadband"].as<float>() : pid.getCurrentDeadband();
                pid.setSafetyParams(deadband, margin);
                sendResponse("Safety parameters updated");
            } else {
                sendResponse("Safety parameters missing");
            }

        } else if (action == "set_output_limits") {
            JsonObject params = cmd["params"];
            if (!params.isNull() && params.containsKey("heating") && params.containsKey("cooling")) {
                float heating = params["heating"];
                float cooling = params["cooling"];
                pid.setOutputLimits(cooling, heating);
                sendResponse("Output limits updated");
            } else {
                sendResponse("Output limit parameters missing");
            }

        } else if (action == "set_breathing_failsafe") {
            JsonObject params = cmd["params"];
            bool enabled = true;
            if (!params.isNull() && params.containsKey("enabled")) {
                enabled = params["enabled"];
            }
            setBreathingFailsafeEnabled(enabled);
            sendResponse(enabled ? "Breathing failsafe enabled" : "Breathing failsafe disabled");

        } else if (action == "start_asymmetric_autotune") {
            JsonObject params = cmd["params"];
            float target = pid.getTargetTemp();
            float heatingStep = 30.0f;
            float coolingStep = 20.0f;
            unsigned long maxDurationMs = 600000UL;

            if (!params.isNull()) {
                if (params.containsKey("setpoint")) {
                    target = params["setpoint"].as<float>();
                }
                if (params.containsKey("heating_step")) {
                    heatingStep = params["heating_step"].as<float>();
                }
                if (params.containsKey("cooling_step")) {
                    coolingStep = params["cooling_step"].as<float>();
                }
                if (params.containsKey("max_duration_s")) {
                    maxDurationMs = params["max_duration_s"].as<unsigned long>() * 1000UL;
                }
            }

            pid.configureAutotune(target, heatingStep, coolingStep, maxDurationMs);
            pid.startAsymmetricAutotune();
            sendResponse("Asymmetric autotune started");

        } else if (action == "abort_asymmetric_autotune") {
            pid.abortAutotune();
            sendResponse("Asymmetric autotune aborted");
        } else if (action == "apply_asymmetric_autotune") {
            if (pid.applyAutotuneRecommendations()) {
                sendResponse("Asymmetric autotune values applied");
            } else {
                sendResponse("Autotune results not available");
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
            pid.setHeatingPID(value, pid.getHeatingKi(), pid.getHeatingKd());
            String message = "🔥 Heating PID Kp via GUI = ";
            message += String(value, 4);
            sendEvent(message);
            sendResponse("Heating Kp updated");

        } else if (variable == "pid_ki") {
            float value = set["value"];
            pid.setHeatingPID(pid.getHeatingKp(), value, pid.getHeatingKd());
            String message = "🔥 Heating PID Ki via GUI = ";
            message += String(value, 4);
            sendEvent(message);
            sendResponse("Heating Ki updated");

        } else if (variable == "pid_kd") {
            float value = set["value"];
            pid.setHeatingPID(pid.getHeatingKp(), pid.getHeatingKi(), value);
            String message = "🔥 Heating PID Kd via GUI = ";
            message += String(value, 4);
            sendEvent(message);
            sendResponse("Heating Kd updated");

        } else if (variable == "pid_max_output") {
            float value = set["value"];
            pid.setMaxOutputPercent(value);
            sendResponse("Max output limit updated");

        } else if (variable == "pid_heating_limit") {
            float value = set["value"];
            pid.setOutputLimits(pid.getCoolingOutputLimit(), value);
            sendResponse("Heating output limit updated");

        } else if (variable == "pid_cooling_limit") {
            float value = set["value"];
            pid.setOutputLimits(value, pid.getHeatingOutputLimit());
            sendResponse("Cooling output limit updated");

        } else if (variable == "pid_cooling_kp") {
            float value = set["value"];
            pid.setCoolingPID(value, pid.getCoolingKi(), pid.getCoolingKd());
            String message = "🧊 Cooling PID Kp via GUI = ";
            message += String(value, 4);
            sendEvent(message);
            sendResponse("Cooling Kp updated");

        } else if (variable == "pid_cooling_ki") {
            float value = set["value"];
            pid.setCoolingPID(pid.getCoolingKp(), value, pid.getCoolingKd());
            String message = "🧊 Cooling PID Ki via GUI = ";
            message += String(value, 4);
            sendEvent(message);
            sendResponse("Cooling Ki updated");

        } else if (variable == "pid_cooling_kd") {
            float value = set["value"];
            pid.setCoolingPID(pid.getCoolingKp(), pid.getCoolingKi(), value);
            String message = "🧊 Cooling PID Kd via GUI = ";
            message += String(value, 4);
            sendEvent(message);
            sendResponse("Cooling Kd updated");

        } else if (variable == "debug_level") {
            int value = set["value"];
            bool enabled = value > 0;
            pid.enableDebug(enabled);
            eeprom.saveDebugLevel(value);
            sendEvent(enabled
                          ? "\U0001f41e Debug telemetry enabled via GUI"
                          : "\U0001f41e Debug telemetry disabled via GUI");
            sendStatus("debug_level", enabled ? 1 : 0);
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
    doc["breathing_failsafe_enabled"] = isBreathingFailsafeEnabled();
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
    StaticJsonDocument<512> doc;
    doc["failsafe_active"] = isFailsafeActive();
    doc["failsafe_reason"] = getFailsafeReason();
    doc["cooling_plate_temp"] = sensors.getCoolingPlateTemp();
    doc["anal_probe_temp"] = sensors.getRectalTemp();
    doc["pid_output"] = pid.getOutput();
    doc["breath_freq_bpm"] = pressure.getBreathRate();
    doc["breathing_failsafe_enabled"] = isBreathingFailsafeEnabled();
    doc["debug_level"] = pid.isDebugEnabled() ? 1 : 0;
    doc["plate_target_active"] = pid.getActivePlateTarget();
    doc["profile_active"] = profileManager.isActive();
    doc["profile_paused"] = profileManager.isPaused();
    doc["profile_step"] = profileManager.getCurrentStep();
    doc["profile_remaining_time"] = profileManager.getRemainingTime();
    doc["autotune_active"] = pid.isAutotuneActive();
    doc["autotune_status"] = pid.getAutotuneStatus();
    doc["cooling_mode"] = pid.isCooling();
    doc["emergency_stop"] = pid.isEmergencyStop();
    doc["temperature_rate"] = pid.getTemperatureRate();
    doc["asymmetric_autotune_active"] = pid.isAutotuneActive();
    doc["pid_max_output"] = pid.getMaxOutputPercent();
    doc["pid_heating_limit"] = pid.getHeatingOutputLimit();
    doc["pid_cooling_limit"] = pid.getCoolingOutputLimit();
    doc["pid_heating_kp"] = pid.getHeatingKp();
    doc["pid_heating_ki"] = pid.getHeatingKi();
    doc["pid_heating_kd"] = pid.getHeatingKd();
    doc["pid_cooling_kp"] = pid.getCoolingKp();
    doc["pid_cooling_ki"] = pid.getCoolingKi();
    doc["pid_cooling_kd"] = pid.getCoolingKd();
    doc["cooling_rate_limit"] = pid.getCoolingRateLimit();
    doc["deadband"] = pid.getCurrentDeadband();
    doc["safety_margin"] = pid.getSafetyMargin();

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

void CommAPI::sendConfig() {
    StaticJsonDocument<512> doc;
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
    doc["breathing_failsafe_enabled"] = isBreathingFailsafeEnabled();
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
    int debugLevel = pid.isDebugEnabled() ? 1 : 0;
    eeprom.saveDebugLevel(debugLevel);
    eeprom.saveFailsafeTimeout(heartbeatTimeoutMs);
}