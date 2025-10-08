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
                 kDefaultCoolingKp, kDefaultCoolingKi, kDefaultCoolingKd, REVERSE),
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
}

void AsymmetricPIDModule::begin(EEPROMManager &eepromManager) {
    eeprom = &eepromManager;
    loadAsymmetricParams();

    coolingPID.SetSampleTime(kSampleTimeMs);
    heatingPID.SetSampleTime(kSampleTimeMs);

    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(MANUAL);

    pwm.begin();

    comm.sendEvent("🔧 Asymmetric PID controller ready");
}

void AsymmetricPIDModule::update(double currentTemp) {
    if (emergencyStop || isFailsafeActive()) {
        stop();
        return;
    }

    Input = sensors.getCoolingPlateTemp();
    unsigned long now = millis();

    if (!active) {
        finalOutput = 0.0;
        rawPIDOutput = 0.0;
        pwm.setDutyCycle(0);
        currentPwmOutput = 0;
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
    if (!checkSafetyLimits(Input, Setpoint)) {
        return;
    }

    updatePIDMode(error);

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
    finalOutput = (outputSmoothingFactor * lastOutput) +
                  ((1.0 - outputSmoothingFactor) * rawPIDOutput);
    lastOutput = finalOutput;
}

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
    currentParams.cooling_limit = -percent;
    currentParams.heating_limit = percent;

    coolingPID.SetOutputLimits(currentParams.cooling_limit, 0.0);
    heatingPID.SetOutputLimits(0.0, currentParams.heating_limit);

    if (persist && eeprom) {
        eeprom->saveMaxOutput(percent);
        saveAsymmetricParams();
    }
}

void AsymmetricPIDModule::setOutputLimits(float coolingLimit, float heatingLimit) {
    currentParams.cooling_limit = constrain(coolingLimit, -100.0f, 0.0f);
    currentParams.heating_limit = constrain(heatingLimit, 0.0f, 100.0f);

    coolingPID.SetOutputLimits(currentParams.cooling_limit, 0.0);
    heatingPID.SetOutputLimits(0.0, currentParams.heating_limit);
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
        finalOutput = 0.0;
        rawPIDOutput = 0.0;
        pwm.setDutyCycle(0);
        digitalWrite(8, LOW);
        digitalWrite(7, LOW);
        comm.sendEvent("Emergency stop engaged");
    } else {
        comm.sendEvent("Emergency stop cleared");
    }
}

void AsymmetricPIDModule::setCoolingRateLimit(float rate, bool persist) {
    maxCoolingRate = rate;

    if (persist && eeprom) {
        eeprom->saveCoolingRateLimit(rate);
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

void AsymmetricPIDModule::startAsymmetricAutotune() {
    if (autotuneActive) {
        return;
    }
    autotuneActive = true;
    autotuneStatusString = "running";
    comm.sendEvent("🎯 Asymmetric autotune started (placeholder)");
    performCoolingAutotune();
}

void AsymmetricPIDModule::runAsymmetricAutotune() {
    if (!autotuneActive) {
        return;
    }
    static unsigned long autotuneStart = 0;
    if (autotuneStart == 0) {
        autotuneStart = millis();
    }
    if (millis() - autotuneStart > 30000) {
        autotuneActive = false;
        autotuneStatusString = "done";
        comm.sendEvent("🎯 Asymmetric autotune completed (placeholder)");
        autotuneStart = 0;
    }
}

void AsymmetricPIDModule::performCoolingAutotune() {
    comm.sendEvent("❄️ Performing cooling autotune (placeholder)");
}

void AsymmetricPIDModule::performHeatingAutotune() {
    comm.sendEvent("🔥 Performing heating autotune (placeholder)");
}

void AsymmetricPIDModule::abortAutotune() {
    autotuneActive = false;
    autotuneStatusString = "aborted";
    comm.sendEvent("⛔ Asymmetric autotune aborted");
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
    eeprom->saveCoolingRateLimit(maxCoolingRate);
    eeprom->saveDeadband(currentParams.deadband);
    eeprom->saveSafetyMargin(currentParams.safety_margin);
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
    float maxOutput = kDefaultMaxOutputPercent;
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

        eeprom->loadMaxOutput(maxOutput);
        if (shouldRestoreMaxOutput(maxOutput)) {
            maxOutput = kDefaultMaxOutputPercent;
            eeprom->saveMaxOutput(maxOutput);
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
    setMaxOutputPercent(maxOutput, false);
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
    coolingPID.SetMode(AUTOMATIC);
    heatingPID.SetMode(AUTOMATIC);
    comm.sendEvent("🚀 Asymmetric PID started");
}

void AsymmetricPIDModule::stop() {
    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(MANUAL);
    active = false;
    finalOutput = 0.0;
    rawPIDOutput = 0.0;
    coolingOutput = 0.0;
    heatingOutput = 0.0;
    pwm.setDutyCycle(0);
    digitalWrite(8, LOW);
    digitalWrite(7, LOW);
    comm.sendEvent("⏹️ Asymmetric PID stopped");
}

bool AsymmetricPIDModule::isActive() {
    return active;
}
