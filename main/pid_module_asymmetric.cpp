#include "pid_module_asymmetric.h"

#include "comm_api.h"
#include "sensor_module.h"

#include <Arduino.h>
#include <ArduinoJson.h>
#include <PID_v1.h>
#include <math.h>

extern SensorModule sensors;
extern CommAPI comm;

int currentPwmOutput = 0;

namespace {
constexpr float kDefaultHeatingKp = 2.0f;
constexpr float kDefaultHeatingKi = 0.5f;
constexpr float kDefaultHeatingKd = 1.0f;

constexpr float kDefaultCoolingKp = 1.5f;
constexpr float kDefaultCoolingKi = 0.3f;
constexpr float kDefaultCoolingKd = 0.8f;

constexpr float kDefaultTargetTemp = 37.0f;
constexpr float kDefaultMaxOutputPercent = 35.0f;
constexpr float kDefaultDeadband = 0.5f;
constexpr float kDefaultSafetyMargin = 2.0f;
constexpr float kDefaultCoolingRate = 2.0f;
constexpr double kOutputSmoothingFactor = 0.8;
constexpr unsigned long kSampleTimeMs = 100;

bool isInvalidValue(float value) {
    return isnan(value) || isinf(value);
}

bool shouldRestorePID(float kp, float ki, float kd) {
    if (isInvalidValue(kp) || isInvalidValue(ki) || isInvalidValue(kd)) {
        return true;
    }
    return kp == 0.0f && ki == 0.0f && kd == 0.0f;
}

bool shouldRestoreTarget(float target) {
    if (isInvalidValue(target)) {
        return true;
    }
    return target < 30.0f || target > 40.0f;
}

bool shouldRestoreMaxOutput(float percent) {
    if (isInvalidValue(percent)) {
        return true;
    }
    return percent <= 0.0f || percent > 100.0f;
}

bool shouldRestoreCoolingRate(float rate) {
    if (isInvalidValue(rate)) {
        return true;
    }
    return rate <= 0.0f || rate > 5.0f;
}

bool shouldRestoreDeadband(float deadband) {
    if (isInvalidValue(deadband)) {
        return true;
    }
    return deadband < 0.1f || deadband > 5.0f;
}

bool shouldRestoreSafetyMargin(float margin) {
    if (isInvalidValue(margin)) {
        return true;
    }
    return margin < 0.1f || margin > 5.0f;
}
}  // namespace

AsymmetricPIDModule::AsymmetricPIDModule()
    : coolingPID(&Input, &coolingOutput, &Setpoint,
                 kDefaultCoolingKp, kDefaultCoolingKi, kDefaultCoolingKd, DIRECT),
      heatingPID(&Input, &heatingOutput, &Setpoint,
                 kDefaultHeatingKp, kDefaultHeatingKi, kDefaultHeatingKd, DIRECT),
      Input(0.0), Setpoint(kDefaultTargetTemp), rawPIDOutput(0.0), finalOutput(0.0),
      coolingOutput(0.0), heatingOutput(0.0),
      active(false), coolingMode(false), emergencyStop(false), autotuneActive(false),
      autotuneStatusString("idle"), debugEnabled(false),
      maxCoolingRate(kDefaultCoolingRate), lastUpdateTime(0),
      lastTemperature(0.0), temperatureRate(0.0),
      outputSmoothingFactor(kOutputSmoothingFactor), lastOutput(0.0),
      eeprom(nullptr) {

    // Initialize default parameters
    currentParams.kp_cooling = kDefaultCoolingKp;
    currentParams.ki_cooling = kDefaultCoolingKi;
    currentParams.kd_cooling = kDefaultCoolingKd;
    currentParams.kp_heating = kDefaultHeatingKp;
    currentParams.ki_heating = kDefaultHeatingKi;
    currentParams.kd_heating = kDefaultHeatingKd;
    currentParams.cooling_limit = -kDefaultMaxOutputPercent;
    currentParams.heating_limit = kDefaultMaxOutputPercent;
    currentParams.deadband = kDefaultDeadband;
    currentParams.safety_margin = kDefaultSafetyMargin;

    autotuneLogIndex = 0;
    autotuneStartMillis = 0;
    lastAutotuneSample = 0;
    autotuneStepPercent = 0.0f;
}

void AsymmetricPIDModule::begin(EEPROMManager &eepromManager) {
    eeprom = &eepromManager;
    loadAsymmetricParams();

    // Configure both PID controllers
    coolingPID.SetSampleTime(kSampleTimeMs);
    heatingPID.SetSampleTime(kSampleTimeMs);

    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(MANUAL);

    pwm.begin();

    comm.sendEvent("🔧 Asymmetric PID controller ready");
}

void AsymmetricPIDModule::update(double /*currentTemp*/) {
    if (emergencyStop || isFailsafeActive()) {
        stop();
        return;
    }

    Input = sensors.getCoolingPlateTemp();
    unsigned long now = millis();

    if (autotuneActive) {
        runAsymmetricAutotune();
        return;
    }

    if (!active) {
        resetOutputState();
        return;
    }

    if (lastUpdateTime != 0) {
        double deltaT = static_cast<double>(now - lastUpdateTime) / 1000.0;
        if (deltaT > 0.0) {
            temperatureRate = (Input - lastTemperature) / deltaT;
        }
    }
    lastUpdateTime = now;
    lastTemperature = Input;

    if (temperatureRate < -maxCoolingRate) {
        setEmergencyStop(true);
        comm.sendEvent("🚨 Cooling rate exceeded safety limit");
        return;
    }

    double error = Setpoint - Input;
    updatePIDMode(error);

    if (!checkSafetyLimits(Input, Setpoint)) {
        return;
    }

    if (coolingMode) {
        coolingPID.Compute();
        rawPIDOutput = coolingOutput;
    } else {
        heatingPID.Compute();
        rawPIDOutput = heatingOutput;
    }

    applySafetyConstraints();
    applyRateLimiting();
    applyOutputSmoothing();

    double magnitude = fabs(finalOutput);
    int pwmValue = constrain(static_cast<int>(magnitude * MAX_PWM / 100.0), 0, MAX_PWM);

    if (finalOutput > 0.0) {
        digitalWrite(8, LOW);
        digitalWrite(7, HIGH);
    } else if (finalOutput < 0.0) {
        digitalWrite(8, HIGH);
        digitalWrite(7, LOW);
    } else {
        digitalWrite(8, LOW);
        digitalWrite(7, LOW);
    }

    pwm.setDutyCycle(pwmValue);
    currentPwmOutput = static_cast<int>(finalOutput);
}

void AsymmetricPIDModule::updatePIDMode(double error) {
    bool wantCooling = error < -currentParams.deadband;
    bool wantHeating = error > currentParams.deadband;

    if (wantCooling && !coolingMode) {
        switchToCoolingPID();
    } else if (wantHeating && coolingMode) {
        switchToHeatingPID();
    }
}

void AsymmetricPIDModule::switchToCoolingPID() {
    coolingMode = true;
    heatingPID.SetMode(MANUAL);
    resetOutputState();
    coolingPID.SetTunings(currentParams.kp_cooling,
                          currentParams.ki_cooling,
                          currentParams.kd_cooling);
    coolingPID.SetOutputLimits(currentParams.cooling_limit, 0.0);
    coolingPID.SetMode(AUTOMATIC);
    comm.sendEvent("❄️ Switched to cooling mode");
}

void AsymmetricPIDModule::switchToHeatingPID() {
    coolingMode = false;
    coolingPID.SetMode(MANUAL);
    resetOutputState();
    heatingPID.SetTunings(currentParams.kp_heating,
                          currentParams.ki_heating,
                          currentParams.kd_heating);
    heatingPID.SetOutputLimits(0.0, currentParams.heating_limit);
    heatingPID.SetMode(AUTOMATIC);
    comm.sendEvent("🔥 Switched to heating mode");
}

bool AsymmetricPIDModule::checkSafetyLimits(double currentTemp, double targetTemp) {
    if (coolingMode && currentTemp <= targetTemp - currentParams.safety_margin) {
        setEmergencyStop(true);
        comm.sendEvent("🚨 Safety margin exceeded during cooling");
        return false;
    }

    if (currentTemp < 10.0 || currentTemp > 45.0) {
        setEmergencyStop(true);
        comm.sendEvent("🚨 Temperature outside safe range");
        return false;
    }

    return true;
}

void AsymmetricPIDModule::applySafetyConstraints() {
    if (coolingMode) {
        double distance = fabs(Input - Setpoint);
        if (distance < 2.0) {
            double scale = distance / 2.0;
            rawPIDOutput *= scale;
        }
        rawPIDOutput = max(rawPIDOutput, static_cast<double>(currentParams.cooling_limit));
    } else {
        rawPIDOutput = min(rawPIDOutput, static_cast<double>(currentParams.heating_limit));
    }
}

void AsymmetricPIDModule::applyRateLimiting() {
    const double maxDelta = static_cast<double>(maxCoolingRate) * 20.0;
    double delta = rawPIDOutput - lastOutput;
    if (delta > maxDelta) {
        rawPIDOutput = lastOutput + maxDelta;
    } else if (delta < -maxDelta) {
        rawPIDOutput = lastOutput - maxDelta;
    }
}

void AsymmetricPIDModule::applyOutputSmoothing() {
    // Smooth output changes to prevent sudden jumps
    finalOutput = (outputSmoothingFactor * lastOutput) +
                  ((1.0 - outputSmoothingFactor) * rawPIDOutput);
    lastOutput = finalOutput;
}

void AsymmetricPIDModule::resetOutputState() {
    rawPIDOutput = 0.0;
    finalOutput = 0.0;
    coolingOutput = 0.0;
    heatingOutput = 0.0;
    lastOutput = 0.0;
    pwm.setDutyCycle(0);
    currentPwmOutput = 0;
}

// --- Compatibility-style getters (preserve existing API) ---
float AsymmetricPIDModule::getKp() {
    return coolingMode ? currentParams.kp_cooling : currentParams.kp_heating;
}

float AsymmetricPIDModule::getKi() {
    return coolingMode ? currentParams.ki_cooling : currentParams.ki_heating;
}

float AsymmetricPIDModule::getKd() {
    return coolingMode ? currentParams.kd_cooling : currentParams.kd_heating;
}

float AsymmetricPIDModule::getMaxOutputPercent() {
    return coolingMode ? fabs(currentParams.cooling_limit) : currentParams.heating_limit;
}

const char *AsymmetricPIDModule::getAutotuneStatus() {
    return autotuneStatusString;
}

void AsymmetricPIDModule::setKp(float value) {
    if (coolingMode) {
        setCoolingPID(value, currentParams.ki_cooling, currentParams.kd_cooling);
    } else {
        setHeatingPID(value, currentParams.ki_heating, currentParams.kd_heating);
    }
}

void AsymmetricPIDModule::setKi(float value) {
    if (coolingMode) {
        setCoolingPID(currentParams.kp_cooling, value, currentParams.kd_cooling);
    } else {
        setHeatingPID(currentParams.kp_heating, value, currentParams.kd_heating);
    }
}

void AsymmetricPIDModule::setKd(float value) {
    if (coolingMode) {
        setCoolingPID(currentParams.kp_cooling, currentParams.ki_cooling, value);
    } else {
        setHeatingPID(currentParams.kp_heating, currentParams.ki_heating, value);
    }
}

void AsymmetricPIDModule::setMaxOutputPercent(float percent, bool persist) {
    percent = constrain(percent, 0.0f, 100.0f);
    setOutputLimits(percent, percent, persist);
}

void AsymmetricPIDModule::setOutputLimits(float coolingLimit, float heatingLimit, bool persist) {
    float constrainedCooling = constrain(coolingLimit, 0.0f, 100.0f);
    float constrainedHeating = constrain(heatingLimit, 0.0f, 100.0f);

    currentParams.cooling_limit = -constrainedCooling;
    currentParams.heating_limit = constrainedHeating;

    coolingPID.SetOutputLimits(currentParams.cooling_limit, 0.0);
    heatingPID.SetOutputLimits(0.0, currentParams.heating_limit);

    if (persist) {
        saveAsymmetricParams();
    }
}

void AsymmetricPIDModule::setCoolingPID(float kp, float ki, float kd, bool persist) {
    currentParams.kp_cooling = kp;
    currentParams.ki_cooling = ki;
    currentParams.kd_cooling = kd;

    if (coolingMode) {
        coolingPID.SetTunings(kp, ki, kd);
    }

    if (persist) {
        saveAsymmetricParams();
        comm.sendEvent("Cooling PID parameters updated");
    }
}

void AsymmetricPIDModule::setHeatingPID(float kp, float ki, float kd, bool persist) {
    currentParams.kp_heating = kp;
    currentParams.ki_heating = ki;
    currentParams.kd_heating = kd;

    if (!coolingMode) {
        heatingPID.SetTunings(kp, ki, kd);
    }

    if (persist) {
        saveAsymmetricParams();
        comm.sendEvent("Heating PID parameters updated");
    }
}

void AsymmetricPIDModule::setEmergencyStop(bool enabled) {
    emergencyStop = enabled;

    if (enabled) {
        active = false;
        resetOutputState();
        digitalWrite(8, LOW);
        digitalWrite(7, LOW);
        comm.sendEvent("Emergency stop engaged");
    } else {
        comm.sendEvent("Emergency stop cleared");
    }
}

void AsymmetricPIDModule::setCoolingRateLimit(float rate, bool persist) {
    maxCoolingRate = rate;

    if (persist) {
        saveAsymmetricParams();
    }

    if (persist) {
        String message = "Cooling rate limit set to ";
        message += String(rate, 2);
        message += " deg/s";
        comm.sendEvent(message);
    }
}

void AsymmetricPIDModule::setSafetyParams(float deadband, float safetyMargin, bool persist) {
    currentParams.deadband = deadband;
    currentParams.safety_margin = safetyMargin;

    if (persist) {
        saveAsymmetricParams();
        String message = "Safety params updated: deadband=";
        message += String(deadband, 2);
        message += " degC, margin=";
        message += String(safetyMargin, 2);
        message += " degC";
        comm.sendEvent(message);
    }
}

void AsymmetricPIDModule::startAutotune() {
    startAsymmetricAutotune();
}

void AsymmetricPIDModule::startAsymmetricAutotune(float requestedStepPercent, const char* direction) {
    if (autotuneActive) {
        comm.sendEvent("⚠️ Asymmetric autotune already running");
        return;
    }

    String directionStr = direction ? String(direction) : String("heating");
    directionStr.toLowerCase();
    if (directionStr == "cooling") {
        comm.sendEvent("⚠️ Cooling autotune er ikke implementert enda");
        autotuneStatusString = "aborted";
        return;
    }

    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(MANUAL);
    active = false;
    resetOutputState();

    resetAutotuneState();
    autotuneActive = true;
    autotuneStatusString = "running";

    float heatingLimit = fabs(currentParams.heating_limit);
    if (heatingLimit < 5.0f) {
        heatingLimit = 5.0f;
    }
    float maxStep = heatingLimit < 35.0f ? heatingLimit : 35.0f;
    float stepPercent = requestedStepPercent;
    if (isnan(stepPercent) || stepPercent <= 0.0f) {
        stepPercent = heatingLimit * 0.35f;
    }
    stepPercent = constrain(stepPercent, 5.0f, maxStep);

    autotuneStepPercent = stepPercent;
    applyManualOutputPercent(stepPercent);

    String message = "🎯 Asymmetric autotune started: applying ";
    message += String(stepPercent, 1);
    message += "% heating step";
    comm.sendEvent(message);
}

void AsymmetricPIDModule::runAsymmetricAutotune() {
    if (!autotuneActive) {
        return;
    }
    unsigned long now = millis();

    if (now - lastAutotuneSample < kAutotuneSampleIntervalMs) {
        return;
    }

    lastAutotuneSample = now;

    if (autotuneLogIndex < kAutotuneLogSize) {
        float temp = sensors.getCoolingPlateTemp();

        autotuneTimestamps[autotuneLogIndex] = now - autotuneStartMillis;
        autotuneTemperatures[autotuneLogIndex] = temp;
        autotuneLogIndex++;

        if (autotuneLogIndex % 5 == 0) {
            StaticJsonDocument<192> doc;
            doc["autotune_time"] = now - autotuneStartMillis;
            doc["autotune_temp"] = temp;
            doc["autotune_progress"] = (autotuneLogIndex * 100) / kAutotuneLogSize;
            doc["autotune_output"] = autotuneStepPercent;
            serializeJson(doc, Serial);
            Serial.println();
        }

        if (autotuneLogIndex >= kAutotuneLogSize) {
            finalizeAutotune(true);
            return;
        }
    }

    if (now - autotuneStartMillis > kAutotuneTimeoutMs) {
        comm.sendEvent("Autotune aborted: timeout reached");
        finalizeAutotune(false);
        return;
    }
}

void AsymmetricPIDModule::performCoolingAutotune() {
    comm.sendEvent("❄️ Performing cooling autotune (placeholder)");
}

void AsymmetricPIDModule::performHeatingAutotune() {
    comm.sendEvent("🔥 Performing heating autotune (placeholder)");
}

void AsymmetricPIDModule::resetAutotuneState() {
    autotuneLogIndex = 0;
    autotuneStartMillis = millis();
    lastAutotuneSample = 0;
    autotuneStepPercent = 0.0f;
}

void AsymmetricPIDModule::applyManualOutputPercent(float percent) {
    percent = constrain(percent, -100.0f, 100.0f);

    rawPIDOutput = percent;
    finalOutput = percent;
    lastOutput = percent;

    int pwmValue = constrain(static_cast<int>(fabs(percent) * MAX_PWM / 100.0f), 0, MAX_PWM);
    if (percent > 0.0f) {
        digitalWrite(8, LOW);
        digitalWrite(7, HIGH);
    } else if (percent < 0.0f) {
        digitalWrite(8, HIGH);
        digitalWrite(7, LOW);
    } else {
        digitalWrite(8, LOW);
        digitalWrite(7, LOW);
    }

    pwm.setDutyCycle(pwmValue);
    currentPwmOutput = static_cast<int>(percent);
}

void AsymmetricPIDModule::finalizeAutotune(bool success) {
    applyManualOutputPercent(0.0f);
    resetOutputState();

    autotuneActive = false;
    lastAutotuneSample = 0;

    if (success) {
        if (calculateAutotuneResults()) {
            autotuneStatusString = "done";
            comm.sendEvent("🎯 Asymmetric autotune completed");
        } else {
            autotuneStatusString = "aborted";
        }
    } else {
        autotuneStatusString = "aborted";
    }

    autotuneStepPercent = 0.0f;
    autotuneStartMillis = 0;
    autotuneLogIndex = 0;
}

bool AsymmetricPIDModule::calculateAutotuneResults() {
    if (autotuneLogIndex < 10) {
        comm.sendEvent("Autotune aborted: insufficient samples");
        return false;
    }

    float initialTemp = autotuneTemperatures[0];
    float finalTemp = autotuneTemperatures[autotuneLogIndex - 1];
    float deltaTemp = finalTemp - initialTemp;
    float stepFraction = autotuneStepPercent / 100.0f;

    if (fabs(deltaTemp) < 0.1f || stepFraction <= 0.0f) {
        comm.sendEvent("Autotune aborted: unstable step response");
        return false;
    }

    float targetTemp = initialTemp + 0.63f * deltaTemp;
    float t63 = 0.0f;

    for (size_t i = 1; i < autotuneLogIndex; ++i) {
        if ((deltaTemp > 0 && autotuneTemperatures[i] >= targetTemp) ||
            (deltaTemp < 0 && autotuneTemperatures[i] <= targetTemp)) {
            t63 = autotuneTimestamps[i] / 1000.0f;
            break;
        }
    }

    if (t63 <= 0.0f) {
        t63 = autotuneTimestamps[autotuneLogIndex - 1] / 2000.0f;
    }

    float deadTime = 1.0f;
    float timeConstant = t63 / 0.63f;
    float processGain = deltaTemp / stepFraction;

    if (timeConstant <= 0.01f || fabs(processGain) < 1e-6f) {
        comm.sendEvent("Autotune aborted: invalid process parameters");
        return false;
    }

    float newKp = 1.2f / (processGain * (deadTime / timeConstant));
    float newKi = newKp / (2.0f * deadTime);
    float newKd = newKp * deadTime * 0.5f;

    newKp = constrain(newKp, 0.05f, 20.0f);
    newKi = constrain(newKi, 0.001f, 5.0f);
    newKd = constrain(newKd, 0.001f, 10.0f);

    setHeatingPID(newKp, newKi, newKd, true);

    StaticJsonDocument<256> doc;
    JsonObject results = doc["autotune_results"].to<JsonObject>();
    results["kp"] = newKp;
    results["ki"] = newKi;
    results["kd"] = newKd;
    results["process_gain"] = processGain;
    results["time_constant"] = timeConstant;
    results["step_percent"] = autotuneStepPercent;
    results["delta_temp"] = deltaTemp;
    serializeJson(doc, Serial);
    Serial.println();

    Serial.print("[Autotune] Heating PID -> Kp=");
    Serial.print(newKp, 4);
    Serial.print(", Ki=");
    Serial.print(newKi, 4);
    Serial.print(", Kd=");
    Serial.println(newKd, 4);

    return true;
}

void AsymmetricPIDModule::abortAutotune() {
    if (!autotuneActive) {
        return;
    }
    comm.sendEvent("⛔ Asymmetric autotune aborted");
    finalizeAutotune(false);
}

void AsymmetricPIDModule::saveAsymmetricParams() {
    if (!eeprom) {
        return;
    }

    eeprom->saveHeatingPIDParams(currentParams.kp_heating,
                                 currentParams.ki_heating,
                                 currentParams.kd_heating);
    eeprom->saveCoolingPIDParams(currentParams.kp_cooling,
                                 currentParams.ki_cooling,
                                 currentParams.kd_cooling);

    EEPROMManager::OutputLimits limits{
        fabs(currentParams.heating_limit),
        fabs(currentParams.cooling_limit),
    };
    eeprom->saveOutputLimits(limits);

    EEPROMManager::SafetySettings safety{
        maxCoolingRate,
        currentParams.deadband,
        currentParams.safety_margin,
    };
    eeprom->saveSafetySettings(safety);

    eeprom->saveTargetTemp(Setpoint);
}

void AsymmetricPIDModule::loadAsymmetricParams() {
    bool restoredDefaults = false;

    float heatingKp = kDefaultHeatingKp;
    float heatingKi = kDefaultHeatingKi;
    float heatingKd = kDefaultHeatingKd;
    float coolingKp = kDefaultCoolingKp;
    float coolingKi = kDefaultCoolingKi;
    float coolingKd = kDefaultCoolingKd;
    float target = kDefaultTargetTemp;
    float heatingLimit = kDefaultMaxOutputPercent;
    float coolingLimit = kDefaultMaxOutputPercent;
    float storedRate = kDefaultCoolingRate;
    float storedDeadband = kDefaultDeadband;
    float storedMargin = kDefaultSafetyMargin;

    if (eeprom) {
        eeprom->loadHeatingPIDParams(heatingKp, heatingKi, heatingKd);
        if (shouldRestorePID(heatingKp, heatingKi, heatingKd)) {
            heatingKp = kDefaultHeatingKp;
            heatingKi = kDefaultHeatingKi;
            heatingKd = kDefaultHeatingKd;
            eeprom->saveHeatingPIDParams(heatingKp, heatingKi, heatingKd);
            restoredDefaults = true;
        }

        eeprom->loadCoolingPIDParams(coolingKp, coolingKi, coolingKd);
        if (shouldRestorePID(coolingKp, coolingKi, coolingKd)) {
            coolingKp = kDefaultCoolingKp;
            coolingKi = kDefaultCoolingKi;
            coolingKd = kDefaultCoolingKd;
            eeprom->saveCoolingPIDParams(coolingKp, coolingKi, coolingKd);
            restoredDefaults = true;
        }

        eeprom->loadTargetTemp(target);
        if (shouldRestoreTarget(target)) {
            target = kDefaultTargetTemp;
            eeprom->saveTargetTemp(target);
            restoredDefaults = true;
        }

        eeprom->loadHeatingMaxOutput(heatingLimit);
        if (shouldRestoreMaxOutput(heatingLimit)) {
            heatingLimit = kDefaultMaxOutputPercent;
            eeprom->saveHeatingMaxOutput(heatingLimit);
            restoredDefaults = true;
        }

        eeprom->loadCoolingMaxOutput(coolingLimit);
        if (shouldRestoreMaxOutput(coolingLimit)) {
            coolingLimit = kDefaultMaxOutputPercent;
            eeprom->saveCoolingMaxOutput(coolingLimit);
            restoredDefaults = true;
        }

        eeprom->loadCoolingRateLimit(storedRate);
        if (shouldRestoreCoolingRate(storedRate)) {
            storedRate = kDefaultCoolingRate;
            eeprom->saveCoolingRateLimit(storedRate);
            restoredDefaults = true;
        }

        eeprom->loadDeadband(storedDeadband);
        if (shouldRestoreDeadband(storedDeadband)) {
            storedDeadband = kDefaultDeadband;
            eeprom->saveDeadband(storedDeadband);
            restoredDefaults = true;
        }

        eeprom->loadSafetyMargin(storedMargin);
        if (shouldRestoreSafetyMargin(storedMargin)) {
            storedMargin = kDefaultSafetyMargin;
            eeprom->saveSafetyMargin(storedMargin);
            restoredDefaults = true;
        }
    }

    currentParams.kp_heating = heatingKp;
    currentParams.ki_heating = heatingKi;
    currentParams.kd_heating = heatingKd;
    currentParams.kp_cooling = coolingKp;
    currentParams.ki_cooling = coolingKi;
    currentParams.kd_cooling = coolingKd;
    currentParams.deadband = storedDeadband;
    currentParams.safety_margin = storedMargin;

    setTargetTemp(target);
    setOutputLimits(coolingLimit, heatingLimit, false);
    maxCoolingRate = storedRate;

    heatingPID.SetTunings(currentParams.kp_heating,
                          currentParams.ki_heating,
                          currentParams.kd_heating);
    coolingPID.SetTunings(currentParams.kp_cooling,
                          currentParams.ki_cooling,
                          currentParams.kd_cooling);
    coolingPID.SetOutputLimits(currentParams.cooling_limit, 0.0);
    heatingPID.SetOutputLimits(0.0, currentParams.heating_limit);

    lastOutput = 0.0;
    finalOutput = 0.0;
    rawPIDOutput = 0.0;

    if (restoredDefaults) {
        Serial.println(F("[PID] Restored asymmetric defaults due to invalid EEPROM data"));
    }
}

void AsymmetricPIDModule::enableDebug(bool enable) {
    debugEnabled = enable;
}

bool AsymmetricPIDModule::isDebugEnabled() {
    return debugEnabled;
}

void AsymmetricPIDModule::start() {
    clearFailsafe();
    active = true;
    resetOutputState();
    coolingPID.SetMode(AUTOMATIC);
    heatingPID.SetMode(AUTOMATIC);
    comm.sendEvent("🚀 Asymmetric PID started");
}

void AsymmetricPIDModule::stop() {
    if (autotuneActive) {
        abortAutotune();
    }
    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(MANUAL);
    active = false;
    resetOutputState();
    digitalWrite(8, LOW);
    digitalWrite(7, LOW);
    comm.sendEvent("⏹️ Asymmetric PID stopped");
}

bool AsymmetricPIDModule::isActive() {
    return active;
}
