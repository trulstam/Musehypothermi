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

namespace {
// Rens meta slik at uinitialiserte EEPROM-biter (0xFF) ikke sendes som tekst.
void sanitizeCalibrationMeta(SensorCalibrationMeta &meta, uint8_t tableCount = 0) {
    meta.operatorName[sizeof(meta.operatorName) - 1] = '\0';

    bool invalid = (meta.timestamp == 0 || meta.timestamp == 0xFFFFFFFF ||
                    meta.pointCount == 0 || meta.pointCount > CALIB_MAX_POINTS);

    if (invalid) {
        meta.timestamp = 0;
        meta.pointCount = 0;
        meta.operatorName[0] = '\0';
    }

    if (tableCount > CALIB_MAX_POINTS) {
        tableCount = CALIB_MAX_POINTS;
    }
    if (tableCount > 0) {
        meta.pointCount = tableCount;
    }
}
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
    // The profile upload payload can easily exceed 1 KB when 10 steps are
    // transferred. A too-small document caused the JSON deserialisation to
    // fail silently, which meant the controller never received the profile
    // (and thus ignored subsequent start commands). Allocate a larger buffer
    // so we can parse complete profile uploads without errors. Keep the
    // document static so it lives in global memory instead of the stack; the
    // previous automatic allocation could exhaust SRAM and prevent the MCU
    // from responding on the serial port when calibration commands were used.
    static StaticJsonDocument<3072> doc;
    doc.clear();
    DeserializationError error = deserializeJson(doc, jsonString);

    if (error) {
        sendResponse("JSON parse error");
        return;
    }

    if (doc.containsKey("CMD")) {
        JsonObject cmd = doc["CMD"];
        String action = cmd["action"];
        String state;
        if (cmd["state"].is<const char*>()) {
            state = cmd["state"].as<const char*>();
        }

        JsonObject params;
        if (cmd["params"].is<JsonObject>()) {
            params = cmd["params"].as<JsonObject>();
        }

        if (action == "pid") {
            if (state == "start") {
                bool started = pid.start();
                sendResponse(started ? "PID started" : "PID blocked: panic/failsafe active");
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
            } else if (state == "calibration_table") {
                sendCalibrationTable();
            } else if (state == "get_calibration_table") {
                sendCalibrationTable();
            } else {
                sendResponse("Unknown GET action");
            }

        } else if (action == "add_calibration_point") {
            if (params.isNull() || !params.containsKey("sensor") || !params.containsKey("reference")) {
                sendResponse("Missing sensor or reference");
                return;
            }

            const char* sensor = params["sensor"];
            float reference = params["reference"];

            const char* opName = "";
            if (params.containsKey("operator") && !params["operator"].isNull()) {
                opName = params["operator"];
            }

            bool ok = sensors.addCalibrationPoint(sensor, reference);
            if (!ok) {
                sendResponse("Calibration table full or sensor name invalid");
                return;
            }

            uint8_t plateCount = 0;
            uint8_t rectalCount = 0;
            sensors.getPlateCalibrationTable(plateCount);
            sensors.getRectalCalibrationTable(rectalCount);
            uint8_t pointCount = strcmp(sensor, "rectal") == 0 ? rectalCount : plateCount;
            eeprom.updateCalibrationMeta(sensor, opName, pointCount, static_cast<uint32_t>(millis()));

            sendResponse("Calibration point added");
            sendCalibrationTable();

        } else if (action == "get_calibration_table") {
            sendCalibrationTable();

        } else if (action == "commit_calibration") {
            JsonVariant obj = cmd["state"];
            if (!obj.is<JsonObject>()) {
                sendResponse("Invalid calibration commit payload");
            } else {
                JsonObject payload = obj.as<JsonObject>();
                const char* sensor = payload["sensor"] | nullptr;
                const char* operatorName = payload["operator"] | "";
                uint32_t timestamp = static_cast<uint32_t>(millis());

                if (!sensor) {
                    sendResponse("Missing sensor for calibration commit");
                } else {
                    bool ok = sensors.commitCalibration(sensor, operatorName, timestamp);
                    if (ok) {
                        String msg = "Calibration committed for ";
                        msg += sensor;
                        msg += " by ";
                        msg += operatorName;
                        sendEvent(msg);  // Norsk: logg at kalibrering ble lagret
                        sendResponse("Calibration committed");
                    } else {
                        sendResponse("Calibration commit failed");
                    }
                }
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
                sendResponse("Unknown profile state");
            }

        } else if (action == "failsafe") {
            if (state == "clear") {
                if (isFailsafeActive()) {
                    clearFailsafe();
                    sendResponse("Failsafe cleared");
                    sendEvent("\u2705 Failsafe manually cleared via GUI");
                } else {
                    sendResponse("Failsafe not active");
                }
            } else if (state == "status") {
                sendFailsafeStatus();
            } else {
                sendResponse("Unknown failsafe command");
            }

        } else if (action == "failsafe_clear") {
            // Legacy compatibility
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

        } else if (action == "clear_panic") {
            clearPanic();
            sendEvent("Panic cleared by GUI");
            sendResponse("Panic cleared");

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

        } else if (action == "start_asymmetric_autotune") {
            bool wasActive = pid.isAutotuneActive();
            JsonObject params = cmd["params"];
            float stepPercent = -1.0f;
            float targetDelta = NAN;
            const char* directionCstr = "heating";
            String directionBuffer;
            if (!params.isNull()) {
                if (params.containsKey("step_percent")) {
                    stepPercent = params["step_percent"].as<float>();
                }
                if (params.containsKey("target_delta")) {
                    targetDelta = params["target_delta"].as<float>();
                }
                if (params.containsKey("direction")) {
                    directionBuffer = String(params["direction"].as<const char*>());
                    directionCstr = directionBuffer.c_str();
                }
            }
            pid.startAsymmetricAutotune(stepPercent, directionCstr, targetDelta);
            if (!wasActive && !pid.isAutotuneActive()) {
                sendResponse("Asymmetric autotune not started");
            } else {
                sendResponse("Asymmetric autotune started");
            }

        } else if (action == "abort_asymmetric_autotune") {
            pid.abortAutotune();
            sendResponse("Asymmetric autotune aborted");
        } else if (action == "equilibrium") {
            if (state == "estimate") {
                pid.startEquilibriumEstimation();
                sendResponse("Equilibrium estimation started");
            } else {
                sendResponse("Unknown equilibrium command");
            }
        } else {
            sendResponse("Unknown CMD action");
        }
    }

    if (doc.containsKey("SET")) {
        JsonObject set = doc["SET"];

        // Backwards/alternative format: calibration payload provided directly
        if (!set.containsKey("variable")) {
            if (set.containsKey("calibration_point")) {
                JsonVariant value = set["calibration_point"];
                if (!value.is<JsonObject>()) {
                    sendResponse("Invalid calibration_point payload");
                } else {
                    JsonObject obj = value.as<JsonObject>();
                    const char* sensor = obj["sensor"] | nullptr;
                    float reference = obj["reference"] | NAN;

                    if (!sensor || isnan(reference)) {
                        sendResponse("Missing sensor or reference for calibration_point");
                    } else {
                        bool ok = sensors.addCalibrationPoint(sensor, reference);
                        if (ok) {
                            sendResponse("Calibration point added");
                            String msg = "Added calibration point: ";
                            msg += sensor;
                            msg += " ref=";
                            msg += reference;
                            sendEvent(msg);
                        } else {
                            sendResponse("Calibration point rejected");
                        }
                    }
                }
            } else if (set.containsKey("calibration_commit")) {
                JsonVariant value = set["calibration_commit"];
                if (!value.is<JsonObject>()) {
                    sendResponse("Invalid calibration_commit payload");
                } else {
                    JsonObject obj = value.as<JsonObject>();
                    const char* sensor = obj["sensor"] | nullptr;
                    const char* operatorName = obj["operator"] | "";
                    uint32_t timestamp = obj["timestamp"] | 0;

                    if (!sensor || timestamp == 0) {
                        sendResponse("Missing sensor or timestamp for calibration_commit");
                    } else {
                        bool ok = sensors.commitCalibration(sensor, operatorName, timestamp);
                        if (ok) {
                            sendResponse("Calibration committed");
                            String msg = "Calibration committed for ";
                            msg += sensor;
                            msg += " by ";
                            msg += operatorName;
                            sendEvent(msg);
                        } else {
                            sendResponse("Calibration commit failed");
                        }
                    }
                }
            }
        } else {
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

            } else if (variable == "pid_heating_limit") {
                float value = set["value"];
                pid.setOutputLimits(pid.getCoolingOutputLimit(), value);
                sendResponse("Heating output limit updated");

            } else if (variable == "pid_cooling_limit") {
                float value = set["value"];
                pid.setOutputLimits(value, pid.getHeatingOutputLimit());
                sendResponse("Cooling output limit updated");

            } else if (variable == "calibration_point") {
                JsonVariant value = set["value"];
                if (!value.is<JsonObject>()) {
                    sendResponse("Invalid calibration_point payload");
                } else {
                    JsonObject obj = value.as<JsonObject>();
                    const char* sensor = obj["sensor"] | nullptr;
                    float reference = obj["reference"] | NAN;

                    if (!sensor || isnan(reference)) {
                        sendResponse("Missing sensor or reference for calibration_point");
                    } else {
                        bool ok = sensors.addCalibrationPoint(sensor, reference);
                        if (ok) {
                            sendResponse("Calibration point added");
                            String msg = "Added calibration point: ";
                            msg += sensor;
                            msg += " ref=";
                            msg += reference;
                            sendEvent(msg);
                        } else {
                            sendResponse("Calibration point rejected");
                        }
                    }
                }

            } else if (variable == "pid_cooling_kp") {
                float value = set["value"];
                pid.setCoolingPID(value, pid.getCoolingKi(), pid.getCoolingKd());
                sendResponse("Cooling Kp updated");

            } else if (variable == "pid_cooling_ki") {
                float value = set["value"];
                pid.setCoolingPID(pid.getCoolingKp(), value, pid.getCoolingKd());
                sendResponse("Cooling Ki updated");

            } else if (variable == "pid_cooling_kd") {
                float value = set["value"];
                pid.setCoolingPID(pid.getCoolingKp(), pid.getCoolingKi(), value);
                sendResponse("Cooling Kd updated");

            } else if (variable == "calibration_commit") {
                JsonVariant value = set["value"];
                if (!value.is<JsonObject>()) {
                    sendResponse("Invalid calibration_commit payload");
                } else {
                    JsonObject obj = value.as<JsonObject>();
                    const char* sensor = obj["sensor"] | nullptr;
                    const char* operatorName = obj["operator"] | "";
                    uint32_t timestamp = obj["timestamp"] | 0;

                    if (!sensor || timestamp == 0) {
                        sendResponse("Missing sensor or timestamp for calibration_commit");
                    } else {
                        bool ok = sensors.commitCalibration(sensor, operatorName, timestamp);
                        if (ok) {
                            sendResponse("Calibration committed");
                            String msg = "Calibration committed for ";
                            msg += sensor;
                            msg += " by ";
                            msg += operatorName;
                            sendEvent(msg);
                        } else {
                            sendResponse("Calibration commit failed");
                        }
                    }
                }

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

            } else if (variable == "equilibrium_compensation") {
                bool enable = set["value"];
                pid.setUseEquilibriumCompensation(enable);
                sendResponse(enable ? "Equilibrium compensation enabled" :
                                  "Equilibrium compensation disabled");

            } else if (variable == "breath_check_enabled") {
                bool enable = set["value"];
                setBreathCheckEnabled(enable);
                sendResponse(enable ? "Breath-stop check enabled" :
                                  "Breath-stop check disabled");

            } else {
                sendResponse("Unknown SET variable");
            }
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
    doc["equilibrium_temp"] = pid.getEquilibriumTemp();
    doc["equilibrium_valid"] = pid.isEquilibriumValid();
    doc["equilibrium_estimating"] = pid.isEquilibriumEstimating();
    doc["equilibrium_compensation_active"] = pid.isEquilibriumCompensationEnabled();
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendFailsafeStatus() {
    static StaticJsonDocument<256> doc;
    doc.clear();
    doc["failsafe_active"] = isFailsafeActive();
    doc["failsafe_reason"] = getFailsafeReason();
    doc["breath_check_enabled"] = isBreathCheckEnabled();
    doc["panic_active"] = isPanicActive();
    doc["panic_reason"] = getPanicReason();
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

    doc["cooling_plate_temp"] = plateTemp;  // Kalibrert verdi
    doc["rectal_temp"] = rectalTemp;        // Kalibrert verdi
    doc["anal_probe_temp"] = rectalTemp;    // Legacy alias

    double plateRaw = sensors.getCoolingPlateRawTemp();
    double rectalRaw = sensors.getRectalRawTemp();
    doc["cooling_plate_raw"] = plateRaw;
    doc["rectal_raw"] = rectalRaw;
    doc["cooling_plate_temp_raw"] = plateRaw;  // Legacy alias
    doc["anal_probe_temp_raw"] = rectalRaw;    // Legacy alias
    doc["pid_output"] = pid.getOutput();
    doc["breath_freq_bpm"] = pressure.getBreathRate();
    doc["plate_target_active"] = pid.getActivePlateTarget();
    doc["profile_active"] = profileManager.isActive();
    doc["profile_paused"] = profileManager.isPaused();
    doc["profile_step_index"] = profileManager.getCurrentStep();
    doc["profile_remaining_time"] = profileManager.getRemainingTime();
    doc["autotune_active"] = pid.isAutotuneActive();
    doc["autotune_status"] = pid.getAutotuneStatus();
    doc["cooling_mode"] = pid.isCooling();
    doc["pid_mode"] = pid.isCooling() ? "cooling" : "heating";
    doc["emergency_stop"] = pid.isEmergencyStop();
    doc["temperature_rate"] = pid.getTemperatureRate();
    doc["asymmetric_autotune_active"] = pid.isAutotuneActive();
    doc["equilibrium_temp"] = pid.getEquilibriumTemp();
    doc["equilibrium_valid"] = pid.isEquilibriumValid();
    doc["equilibrium_estimating"] = pid.isEquilibriumEstimating();
    doc["equilibrium_compensation_active"] = pid.isEquilibriumCompensationEnabled();
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

    SensorCalibrationMeta plateMeta{};
    SensorCalibrationMeta rectalMeta{};
    eeprom.getPlateCalibrationMeta(plateMeta);
    eeprom.getRectalCalibrationMeta(rectalMeta);
    uint8_t plateCount = 0;
    uint8_t rectalCount = 0;
    sensors.getPlateCalibrationTable(plateCount);
    sensors.getRectalCalibrationTable(rectalCount);
    sanitizeCalibrationMeta(plateMeta, plateCount);
    sanitizeCalibrationMeta(rectalMeta, rectalCount);

    JsonObject cal = doc.createNestedObject("calibration");
    JsonObject plateObj = cal.createNestedObject("plate");
    plateObj["timestamp"] = plateMeta.timestamp;
    plateObj["operator"] = plateMeta.operatorName;
    plateObj["points"] = plateMeta.pointCount;

    JsonObject rectalObj = cal.createNestedObject("rectal");
    rectalObj["timestamp"] = rectalMeta.timestamp;
    rectalObj["operator"] = rectalMeta.operatorName;
    rectalObj["points"] = rectalMeta.pointCount;

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
    StaticJsonDocument<768> doc;
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
    doc["equilibrium_compensation_active"] = pid.isEquilibriumCompensationEnabled();

    SensorCalibrationMeta plateMeta{};
    SensorCalibrationMeta rectalMeta{};
    eeprom.getPlateCalibrationMeta(plateMeta);
    eeprom.getRectalCalibrationMeta(rectalMeta);
    uint8_t plateCount = 0;
    uint8_t rectalCount = 0;
    sensors.getPlateCalibrationTable(plateCount);
    sensors.getRectalCalibrationTable(rectalCount);
    sanitizeCalibrationMeta(plateMeta, plateCount);
    sanitizeCalibrationMeta(rectalMeta, rectalCount);

    JsonObject cal = doc.createNestedObject("calibration");
    JsonObject plateObj = cal.createNestedObject("plate");
    plateObj["timestamp"] = plateMeta.timestamp;
    plateObj["operator"] = plateMeta.operatorName;
    plateObj["points"] = plateMeta.pointCount;

    JsonObject rectalObj = cal.createNestedObject("rectal");
    rectalObj["timestamp"] = rectalMeta.timestamp;
    rectalObj["operator"] = rectalMeta.operatorName;
    rectalObj["points"] = rectalMeta.pointCount;
    serializeJson(doc, *serial);
    serial->println();
}

void CommAPI::sendCalibrationTable() {
    static StaticJsonDocument<1024> doc;
    doc.clear();
    doc["type"] = "calibration_table";

    SensorCalibrationMeta plateMeta{};
    SensorCalibrationMeta rectalMeta{};
    eeprom.getPlateCalibrationMeta(plateMeta);
    eeprom.getRectalCalibrationMeta(rectalMeta);

    uint8_t plateCount = 0;
    uint8_t rectalCount = 0;
    const CalibrationPoint* plateTable = sensors.getPlateCalibrationTable(plateCount);
    const CalibrationPoint* rectalTable = sensors.getRectalCalibrationTable(rectalCount);
    sanitizeCalibrationMeta(plateMeta, plateCount);
    sanitizeCalibrationMeta(rectalMeta, rectalCount);

    JsonObject plate = doc.createNestedObject("plate");
    JsonObject plateMetaObj = plate.createNestedObject("meta");
    plateMetaObj["timestamp"] = plateMeta.timestamp;
    plateMetaObj["operator"] = plateMeta.operatorName;
    plateMetaObj["count"] = plateMeta.pointCount;

    JsonArray platePoints = plate.createNestedArray("points");
    // Bygg tabell for plate-sensor: målt verdi og referanseverdi til GUI
    if (plateTable) {
        for (uint8_t i = 0; i < plateCount; ++i) {
            JsonObject p = platePoints.createNestedObject();
            p["measured"] = plateTable[i].measured;
            p["reference"] = plateTable[i].reference;
        }
    }

    JsonObject rectal = doc.createNestedObject("rectal");
    JsonObject rectalMetaObj = rectal.createNestedObject("meta");
    rectalMetaObj["timestamp"] = rectalMeta.timestamp;
    rectalMetaObj["operator"] = rectalMeta.operatorName;
    rectalMetaObj["count"] = rectalMeta.pointCount;

    JsonArray rectalPoints = rectal.createNestedArray("points");
    // Bygg tabell for rektal-sensor: målt verdi og referanseverdi til GUI
    if (rectalTable) {
        for (uint8_t i = 0; i < rectalCount; ++i) {
            JsonObject p = rectalPoints.createNestedObject();
            p["measured"] = rectalTable[i].measured;
            p["reference"] = rectalTable[i].reference;
        }
    }

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