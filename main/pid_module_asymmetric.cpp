#include "pid_module_asymmetric.h"

#include "comm_api.h"
#include "sensor_module.h"

#include <Arduino.h>
#include <ArduinoJson.h>
#include <PID_v1.h>
#include <math.h>
#include <algorithm>

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
constexpr float kDefaultMaxOutputPercent = 50.0f;
constexpr float kDefaultDeadband = 0.5f;
constexpr float kDefaultSafetyMargin = 2.0f;
constexpr float kDefaultCoolingRate = 2.0f;
constexpr double kOutputSmoothingFactor = 0.8;
constexpr unsigned long kSampleTimeMs = 100;
constexpr double kDefaultEquilibriumEpsilon = 0.02;
constexpr unsigned long kDefaultEquilibriumStableMs = 60000;
constexpr double kDefaultFeedforwardGain = 15.0;

constexpr float kHeatingKpMin = 0.05f;
constexpr float kHeatingKpMax = 40.0f;
constexpr float kHeatingKiMin = 0.0005f;
constexpr float kHeatingKiMax = 6.0f;
constexpr float kHeatingKdMin = 0.0f;
constexpr float kHeatingKdMax = 12.0f;

constexpr float kCoolingKpMin = 0.02f;
constexpr float kCoolingKpMax = 25.0f;
constexpr float kCoolingKiMin = 0.0005f;
constexpr float kCoolingKiMax = 4.0f;
constexpr float kCoolingKdMin = 0.0f;
constexpr float kCoolingKdMax = 12.0f;

constexpr float kLambdaFloor = 5.0f;
constexpr float kLambdaFactor = 0.8f;

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

struct SegmentStats {
    float stepPercent = 0.0f;
    float deltaTemp = 0.0f;
    float maxRate = 0.0f;
    float deadTime = 0.0f;
    float timeConstant = 0.0f;
    float processGain = 0.0f;
    float overshoot = 0.0f;
    float duration = 0.0f;
    size_t samples = 0;
    float startTemp = 0.0f;
    float endTemp = 0.0f;
};

bool CollectSegmentStats(const unsigned long* timestamps,
                         const float* temperatures,
                         size_t start,
                         size_t end,
                         float stepPercent,
                         float baseline,
                         float targetDelta,
                         bool heating,
                         SegmentStats& out) {
    if (end <= start + 2 || stepPercent == 0.0f) {
        return false;
    }

    float startTemp = temperatures[start];
    float extremeTemp = startTemp;
    size_t extremeIndex = start;
    float maxRate = 0.0f;

    for (size_t i = start + 1; i < end; ++i) {
        float dt = static_cast<float>(timestamps[i] - timestamps[i - 1]) / 1000.0f;
        if (dt <= 0.0f) {
            continue;
        }
        float diff = temperatures[i] - temperatures[i - 1];
        float rate = diff / dt;
        float absRate = fabsf(rate);
        if (absRate > maxRate) {
            maxRate = absRate;
        }
        if (heating) {
            if (temperatures[i] > extremeTemp) {
                extremeTemp = temperatures[i];
                extremeIndex = i;
            }
        } else {
            if (temperatures[i] < extremeTemp) {
                extremeTemp = temperatures[i];
                extremeIndex = i;
            }
        }
    }

    float deltaTemp = heating ? (extremeTemp - startTemp) : (startTemp - extremeTemp);
    if (deltaTemp < 0.05f) {
        return false;
    }

    float stepFraction = fabsf(stepPercent) / 100.0f;
    if (stepFraction <= 1e-4f) {
        return false;
    }

    float processGain = deltaTemp / stepFraction;

    float startTime = static_cast<float>(timestamps[start]) / 1000.0f;
    float target28 = heating ? startTemp + 0.283f * deltaTemp
                             : startTemp - 0.283f * deltaTemp;
    float target63 = heating ? startTemp + 0.632f * deltaTemp
                             : startTemp - 0.632f * deltaTemp;

    float t28 = -1.0f;
    float t63 = -1.0f;

    for (size_t i = start; i < end; ++i) {
        float value = temperatures[i];
        float timeOffset = static_cast<float>(timestamps[i]) / 1000.0f - startTime;

        if (t28 < 0.0f) {
            if (heating ? value >= target28 : value <= target28) {
                t28 = timeOffset;
            }
        }
        if (t63 < 0.0f) {
            if (heating ? value >= target63 : value <= target63) {
                t63 = timeOffset;
            }
        }
        if (t28 >= 0.0f && t63 >= 0.0f) {
            break;
        }
    }

    if (t28 < 0.0f) {
        t28 = 0.25f * static_cast<float>(timestamps[end - 1] - timestamps[start]) / 1000.0f;
    }
    if (t63 < 0.0f) {
        t63 = static_cast<float>(timestamps[end - 1] - timestamps[start]) / 1000.0f;
    }

    float deadTime = 1.5f * t28 - 0.5f * t63;
    if (deadTime < 0.0f) {
        deadTime = 0.0f;
    }
    float timeConstant = t63 - deadTime;
    if (timeConstant < 0.1f) {
        timeConstant = 0.1f;
    }

    float overshoot = 0.0f;
    float expectedPeak = heating ? (baseline + targetDelta) : (baseline - targetDelta);
    if (heating) {
        overshoot = extremeTemp - expectedPeak;
    } else {
        overshoot = expectedPeak - extremeTemp;
    }
    if (overshoot < 0.0f) {
        overshoot = 0.0f;
    }

    out.stepPercent = fabsf(stepPercent);
    out.deltaTemp = deltaTemp;
    out.maxRate = maxRate;
    out.deadTime = deadTime;
    out.timeConstant = timeConstant;
    out.processGain = processGain;
    out.overshoot = overshoot;
    out.duration = static_cast<float>(timestamps[end - 1] - timestamps[start]) / 1000.0f;
    out.samples = end - start;
    out.startTemp = startTemp;
    out.endTemp = extremeTemp;
    return true;
}

bool ComputeImcPid(const SegmentStats& stats,
                   float kpMin,
                   float kpMax,
                   float kiMin,
                   float kiMax,
                   float kdMin,
                   float kdMax,
                   float& outKp,
                   float& outKi,
                   float& outKd) {
    if (stats.processGain <= 1e-6f || stats.timeConstant <= 0.0f) {
        return false;
    }

    float lambda = std::max({kLambdaFactor * stats.timeConstant,
                              2.0f * stats.deadTime,
                              kLambdaFloor});

    float kc = stats.timeConstant / (stats.processGain * (lambda + stats.deadTime));
    if (!isfinite(kc) || kc <= 0.0f) {
        return false;
    }

    float Ti = std::max(stats.timeConstant, 1e-3f);
    float Td = stats.timeConstant * stats.deadTime /
               std::max(2.0f * stats.timeConstant + stats.deadTime, 1e-3f);

    float kp = constrain(kc, kpMin, kpMax);
    float ki = constrain(kc / Ti, kiMin, kiMax);
    float kd = constrain(kc * Td, kdMin, kdMax);

    outKp = kp;
    outKi = ki;
    outKd = kd;
    return true;
}
}  // namespace

const char* AsymmetricPIDModule::PhaseName(AutotunePhase phase) {
    switch (phase) {
        case AutotunePhase::HeatingRamp:
            return "heating_ramp";
        case AutotunePhase::HeatingHold:
            return "heating_hold";
        case AutotunePhase::CoolingRamp:
            return "cooling_ramp";
        case AutotunePhase::CoolingHold:
            return "cooling_hold";
        default:
            return "idle";
    }
}

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
      eeprom(nullptr), equilibriumTemp(0.0), equilibriumValid(false),
      equilibriumTimestamp(0), equilibriumEpsilon(kDefaultEquilibriumEpsilon),
      equilibriumMinStableMs(kDefaultEquilibriumStableMs), lastEquilibriumCheckTemp(0.0),
      lastEquilibriumCheckMillis(0), kff(kDefaultFeedforwardGain) {

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
    autotuneHeatingStepPercent = 0.0f;
    autotuneCoolingStepPercent = 0.0f;
    autotuneTargetDelta = 0.0f;
    autotuneBaselineTemp = 0.0f;
    lastAutotuneOutput = 0.0f;
    autotunePhase = AutotunePhase::Idle;
    autotuneCoolingEnabled = false;
    phaseStartMillis = 0;
    autotuneMode = AutotuneMode::HeatingOnly;
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

    if (!autotuneActive) {
        updateEquilibriumEstimate();
    }

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

    rawPIDOutput += computeFeedforward();

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

void AsymmetricPIDModule::updateEquilibriumEstimate() {
    int pwmMax = MAX_PWM * (getMaxOutputPercent() / 100.0f);
    if (fabs(finalOutput) > 0.05 * pwmMax) {
        lastEquilibriumCheckMillis = 0;
        return;
    }

    unsigned long now = millis();
    if (lastEquilibriumCheckMillis == 0) {
        lastEquilibriumCheckMillis = now;
        lastEquilibriumCheckTemp = Input;
        equilibriumTimestamp = now;
        return;
    }

    double deltaT = Input - lastEquilibriumCheckTemp;
    double deltaTime = static_cast<double>(now - lastEquilibriumCheckMillis) / 1000.0;
    if (deltaTime <= 0.0) {
        return;
    }

    double slope = deltaT / deltaTime;
    bool stable = fabs(slope) < equilibriumEpsilon;

    lastEquilibriumCheckTemp = Input;
    lastEquilibriumCheckMillis = now;

    if (!stable) {
        equilibriumTimestamp = now;
        return;
    }

    if (equilibriumTimestamp == 0) {
        equilibriumTimestamp = now;
    }

    if (now - equilibriumTimestamp >= equilibriumMinStableMs) {
        equilibriumTemp = Input;
        equilibriumValid = true;
    }
}

double AsymmetricPIDModule::computeFeedforward() {
    if (!equilibriumValid) {
        return 0.0;
    }

    double delta = Setpoint - equilibriumTemp;
    double ff = kff * delta;

    double limit = std::max(fabs(static_cast<double>(currentParams.heating_limit)),
                            fabs(static_cast<double>(currentParams.cooling_limit)));
    if (limit <= 0.0) {
        return 0.0;
    }

    ff = constrain(ff, -limit, limit);
    return ff;
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

void AsymmetricPIDModule::startAsymmetricAutotune(float requestedStepPercent,
                                                 const char* direction,
                                                 float requestedDelta) {
    if (autotuneActive) {
        comm.sendEvent("⚠️ Asymmetric autotune already running");
        return;
    }

    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(MANUAL);
    active = false;
    resetOutputState();

    resetAutotuneState();
    autotuneActive = true;
    autotuneStatusString = "running";

    String directionStr = direction ? String(direction) : String("heating");
    directionStr.toLowerCase();

    float targetDelta = requestedDelta;
    if (isnan(targetDelta) || targetDelta <= 0.0f) {
        targetDelta = kAutotuneDefaultDelta;
    }
    targetDelta = constrain(targetDelta, kAutotuneMinDelta, kAutotuneMaxDelta);

    float heatingLimit = fabs(currentParams.heating_limit);
    if (heatingLimit < 5.0f) {
        heatingLimit = 5.0f;
    }
    float coolingLimit = fabs(currentParams.cooling_limit);
    if (coolingLimit < 1.0f) {
        coolingLimit = 0.0f;
    }

    bool requestCoolingOnly = directionStr == "cooling";
    bool requestBoth = directionStr == "both" || directionStr == "dual";

    float stepPercent = requestedStepPercent;
    if (isnan(stepPercent) || stepPercent <= 0.0f) {
        float baseLimit = requestCoolingOnly ? coolingLimit : heatingLimit;
        if (baseLimit <= 0.0f) {
            baseLimit = requestCoolingOnly ? 10.0f : 5.0f;
        }
        stepPercent = baseLimit * 0.6f;
    }

    if (requestCoolingOnly) {
        if (coolingLimit <= 0.0f) {
            comm.sendEvent("⚠️ Cooling autotune er ikke tilgjengelig: kjølegrensen er 0 %");
            autotuneStatusString = "aborted";
            autotuneActive = false;
            return;
        }

        stepPercent = constrain(fabs(stepPercent), 5.0f, coolingLimit);
        autotuneHeatingStepPercent = 0.0f;
        autotuneCoolingStepPercent = -stepPercent;
        autotuneCoolingEnabled = true;
        autotuneTargetDelta = targetDelta;
        autotuneBaselineTemp = sensors.getCoolingPlateTemp();
        autotuneMode = AutotuneMode::CoolingOnly;

        applyManualOutputPercent(autotuneCoolingStepPercent);
        setAutotunePhase(AutotunePhase::CoolingRamp);

        String message = "🎯 Asymmetric autotune started: cooling step ";
        message += String(stepPercent, 1);
        message += "% (target ΔT ";
        message += String(targetDelta, 1);
        message += " °C)";
        comm.sendEvent(message);
        return;
    }

    stepPercent = constrain(fabs(stepPercent), 5.0f, heatingLimit);

    float coolingStep = 0.0f;
    if (coolingLimit > 0.0f && (requestBoth || coolingLimit >= 1.0f)) {
        coolingStep = std::min(stepPercent, coolingLimit);
    }

    autotuneHeatingStepPercent = stepPercent;
    autotuneCoolingStepPercent = coolingStep > 0.0f ? -coolingStep : 0.0f;
    autotuneCoolingEnabled = coolingStep > 0.0f;
    autotuneTargetDelta = targetDelta;
    autotuneBaselineTemp = sensors.getCoolingPlateTemp();
    autotuneMode = autotuneCoolingEnabled ? AutotuneMode::HeatingThenCooling : AutotuneMode::HeatingOnly;

    applyManualOutputPercent(autotuneHeatingStepPercent);
    setAutotunePhase(AutotunePhase::HeatingRamp);

    String message = "🎯 Asymmetric autotune started: heating step ";
    message += String(stepPercent, 1);
    message += "% (target ΔT ";
    message += String(targetDelta, 1);
    message += " °C)";
    if (autotuneCoolingEnabled) {
        message += " – cooling step will follow";
    } else {
        message += " – cooling step unavailable";
    }
    comm.sendEvent(message);

    if (!autotuneCoolingEnabled) {
        comm.sendEvent("⚠️ Cooling autotune skipped: insufficient cooling limit");
    }
}

void AsymmetricPIDModule::runAsymmetricAutotune() {
    if (!autotuneActive) {
        return;
    }
    unsigned long now = millis();

    if (now - autotuneStartMillis > kAutotuneTimeoutMs) {
        comm.sendEvent("Autotune aborted: timeout reached");
        finalizeAutotune(false);
        return;
    }

    if (now - lastAutotuneSample < kAutotuneSampleIntervalMs) {
        return;
    }

    lastAutotuneSample = now;
    float temperature = sensors.getCoolingPlateTemp();

    if (autotuneLogIndex < kAutotuneLogSize) {
        autotuneTimestamps[autotuneLogIndex] = now - autotuneStartMillis;
        autotuneTemperatures[autotuneLogIndex] = temperature;
        autotuneOutputs[autotuneLogIndex] = lastAutotuneOutput;
        autotuneLogIndex++;
        publishAutotuneProgress(now, temperature);
    } else {
        finalizeAutotune(true);
        return;
    }

    float deltaHeating = temperature - autotuneBaselineTemp;
    float deltaCooling = autotuneBaselineTemp - temperature;
    unsigned long phaseElapsed = now - phaseStartMillis;

    switch (autotunePhase) {
        case AutotunePhase::HeatingRamp:
            if (deltaHeating >= autotuneTargetDelta || phaseElapsed >= kAutotuneMaxSegmentMs) {
                applyManualOutputPercent(0.0f);
                setAutotunePhase(AutotunePhase::HeatingHold);
            }
            break;
        case AutotunePhase::HeatingHold:
            if (phaseElapsed >= kAutotuneHoldTimeMs) {
                if (autotuneCoolingEnabled) {
                    applyManualOutputPercent(autotuneCoolingStepPercent);
                    setAutotunePhase(AutotunePhase::CoolingRamp);
                } else {
                    finalizeAutotune(true);
                    return;
                }
            }
            break;
        case AutotunePhase::CoolingRamp:
            if (deltaCooling >= autotuneTargetDelta || phaseElapsed >= kAutotuneMaxSegmentMs) {
                applyManualOutputPercent(0.0f);
                setAutotunePhase(AutotunePhase::CoolingHold);
            }
            break;
        case AutotunePhase::CoolingHold:
            if (phaseElapsed >= kAutotuneHoldTimeMs) {
                finalizeAutotune(true);
                return;
            }
            break;
        case AutotunePhase::Idle:
        default:
            break;
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
    autotuneHeatingStepPercent = 0.0f;
    autotuneCoolingStepPercent = 0.0f;
    autotuneTargetDelta = kAutotuneDefaultDelta;
    autotuneBaselineTemp = sensors.getCoolingPlateTemp();
    lastAutotuneOutput = 0.0f;
    autotunePhase = AutotunePhase::Idle;
    autotuneCoolingEnabled = false;
    phaseStartMillis = autotuneStartMillis;
    autotuneMode = AutotuneMode::HeatingOnly;
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
    lastAutotuneOutput = percent;
}

void AsymmetricPIDModule::setAutotunePhase(AutotunePhase phase) {
    autotunePhase = phase;
    phaseStartMillis = millis();
    autotuneStatusString = PhaseName(phase);
}

void AsymmetricPIDModule::publishAutotuneProgress(unsigned long now, float temperature) {
    StaticJsonDocument<256> doc;
    doc["autotune_time"] = now - autotuneStartMillis;
    doc["autotune_temp"] = temperature;
    doc["autotune_progress"] = static_cast<int>((autotuneLogIndex * 100UL) / kAutotuneLogSize);
    doc["autotune_output"] = lastAutotuneOutput;
    doc["autotune_phase"] = PhaseName(autotunePhase);
    doc["autotune_delta"] = temperature - autotuneBaselineTemp;
    serializeJson(doc, Serial);
    Serial.println();
}

void AsymmetricPIDModule::finalizeAutotune(bool success) {
    applyManualOutputPercent(0.0f);
    resetOutputState();

    autotuneActive = false;
    lastAutotuneSample = 0;
    autotunePhase = AutotunePhase::Idle;
    autotuneCoolingEnabled = false;

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

    autotuneHeatingStepPercent = 0.0f;
    autotuneCoolingStepPercent = 0.0f;
    autotuneStartMillis = 0;
    autotuneLogIndex = 0;
    autotuneMode = AutotuneMode::HeatingOnly;
}

bool AsymmetricPIDModule::calculateAutotuneResults() {
    if (autotuneLogIndex < 10) {
        comm.sendEvent("Autotune aborted: insufficient samples");
        return false;
    }

    const float kOutputThreshold = 1.0f;
    const float kHoldThreshold = 0.5f;

    bool heatingExpected = autotuneMode != AutotuneMode::CoolingOnly;
    bool coolingExpected = autotuneMode == AutotuneMode::CoolingOnly ||
                           (autotuneMode == AutotuneMode::HeatingThenCooling && autotuneCoolingEnabled);

    SegmentStats heatingStats;
    bool heatingPidCalculated = false;
    float heatingKp = currentParams.kp_heating;
    float heatingKi = currentParams.ki_heating;
    float heatingKd = currentParams.kd_heating;
    String heatingReason;

    size_t heatEnd = 0;
    if (heatingExpected) {
        size_t heatStart = SIZE_MAX;
        for (size_t i = 0; i < autotuneLogIndex; ++i) {
            if (autotuneOutputs[i] > kOutputThreshold) {
                heatStart = i;
                break;
            }
        }

        if (heatStart == SIZE_MAX) {
            comm.sendEvent("Autotune aborted: heating step not detected");
            return false;
        }

        heatEnd = heatStart;
        while (heatEnd < autotuneLogIndex && autotuneOutputs[heatEnd] > kHoldThreshold) {
            ++heatEnd;
        }

        if (!CollectSegmentStats(autotuneTimestamps,
                                 autotuneTemperatures,
                                 heatStart,
                                 heatEnd,
                                 autotuneHeatingStepPercent,
                                 autotuneBaselineTemp,
                                 autotuneTargetDelta,
                                 true,
                                 heatingStats)) {
            comm.sendEvent("Autotune aborted: inadequate heating response");
            return false;
        }

        if (!ComputeImcPid(heatingStats,
                           kHeatingKpMin,
                           kHeatingKpMax,
                           kHeatingKiMin,
                           kHeatingKiMax,
                           kHeatingKdMin,
                           kHeatingKdMax,
                           heatingKp,
                           heatingKi,
                           heatingKd)) {
            comm.sendEvent("Autotune aborted: heating PID could not be calculated");
            return false;
        }

        setHeatingPID(heatingKp, heatingKi, heatingKd, true);
        heatingPidCalculated = true;
    } else {
        heatEnd = 0;
        heatingReason = "autotune for varme ble ikke forespurt";
    }

    bool coolingPidCalculated = false;
    SegmentStats coolingStats;
    float coolingKp = currentParams.kp_cooling;
    float coolingKi = currentParams.ki_cooling;
    float coolingKd = currentParams.kd_cooling;
    String coolingReason;

    if (coolingExpected) {
        size_t coolStart = SIZE_MAX;
        for (size_t i = heatEnd; i < autotuneLogIndex; ++i) {
            if (autotuneOutputs[i] < -kOutputThreshold) {
                coolStart = i;
                break;
            }
        }

        if (coolStart != SIZE_MAX) {
            size_t coolEnd = coolStart;
            while (coolEnd < autotuneLogIndex && autotuneOutputs[coolEnd] < -kHoldThreshold) {
                ++coolEnd;
            }

            bool statsOk = CollectSegmentStats(autotuneTimestamps,
                                               autotuneTemperatures,
                                               coolStart,
                                               coolEnd,
                                               autotuneCoolingStepPercent,
                                               autotuneBaselineTemp,
                                               autotuneTargetDelta,
                                               false,
                                               coolingStats);
            bool pidOk = false;
            if (statsOk) {
                pidOk = ComputeImcPid(coolingStats,
                                      kCoolingKpMin,
                                      kCoolingKpMax,
                                      kCoolingKiMin,
                                      kCoolingKiMax,
                                      kCoolingKdMin,
                                      kCoolingKdMax,
                                      coolingKp,
                                      coolingKi,
                                      coolingKd);
            }

            if (statsOk && pidOk) {
                setCoolingPID(coolingKp, coolingKi, coolingKd, true);
                coolingPidCalculated = true;
            } else {
                coolingReason = "mangelfull kjølerespons";
                if (autotuneMode == AutotuneMode::CoolingOnly) {
                    comm.sendEvent("Autotune aborted: cooling PID could not be calculated");
                    return false;
                }
            }
        } else {
            coolingReason = "fant ikke kjøletrinn";
            if (autotuneMode == AutotuneMode::CoolingOnly) {
                comm.sendEvent("Autotune aborted: cooling step not detected");
                return false;
            }
        }
    } else {
        coolingReason = "autotune for kjøling ble hoppet over";
    }

    StaticJsonDocument<768> doc;
    JsonObject root = doc["autotune_results"].to<JsonObject>();

    root["kp"] = heatingPidCalculated ? heatingKp : currentParams.kp_heating;
    root["ki"] = heatingPidCalculated ? heatingKi : currentParams.ki_heating;
    root["kd"] = heatingPidCalculated ? heatingKd : currentParams.kd_heating;

    JsonObject heating = root.createNestedObject("heating");
    heating["available"] = heatingPidCalculated;
    if (heatingPidCalculated) {
        heating["kp"] = heatingKp;
        heating["ki"] = heatingKi;
        heating["kd"] = heatingKd;
        heating["process_gain"] = heatingStats.processGain;
        heating["dead_time"] = heatingStats.deadTime;
        heating["time_constant"] = heatingStats.timeConstant;
        heating["delta_temp"] = heatingStats.deltaTemp;
        heating["max_rate"] = heatingStats.maxRate;
        heating["overshoot"] = heatingStats.overshoot;
        heating["duration"] = heatingStats.duration;
        heating["sample_count"] = static_cast<int>(heatingStats.samples);
        heating["step_percent"] = heatingStats.stepPercent;
        heating["start_temp"] = heatingStats.startTemp;
        heating["end_temp"] = heatingStats.endTemp;
    } else if (heatingReason.length() > 0) {
        heating["reason"] = heatingReason;
    }

    JsonObject cooling = root.createNestedObject("cooling");
    if (coolingPidCalculated) {
        cooling["kp"] = coolingKp;
        cooling["ki"] = coolingKi;
        cooling["kd"] = coolingKd;
        cooling["process_gain"] = coolingStats.processGain;
        cooling["dead_time"] = coolingStats.deadTime;
        cooling["time_constant"] = coolingStats.timeConstant;
        cooling["delta_temp"] = coolingStats.deltaTemp;
        cooling["max_rate"] = coolingStats.maxRate;
        cooling["overshoot"] = coolingStats.overshoot;
        cooling["duration"] = coolingStats.duration;
        cooling["sample_count"] = static_cast<int>(coolingStats.samples);
        cooling["step_percent"] = coolingStats.stepPercent;
        cooling["start_temp"] = coolingStats.startTemp;
        cooling["end_temp"] = coolingStats.endTemp;
        cooling["available"] = true;
    } else {
        cooling["available"] = false;
        if (coolingReason.length() > 0) {
            cooling["reason"] = coolingReason;
        }
    }

    JsonObject meta = root.createNestedObject("meta");
    meta["baseline_temp"] = autotuneBaselineTemp;
    meta["target_delta"] = autotuneTargetDelta;
    meta["duration"] = static_cast<float>(autotuneTimestamps[autotuneLogIndex - 1]) / 1000.0f;
    meta["sample_count"] = static_cast<int>(autotuneLogIndex);
    meta["heating_step_percent"] = autotuneHeatingStepPercent;
    meta["cooling_step_percent"] = fabsf(autotuneCoolingStepPercent);
    meta["cooling_enabled"] = coolingPidCalculated;
    meta["primary_direction"] = autotuneMode == AutotuneMode::CoolingOnly ? "cooling" : "heating";
    meta["mode"] = static_cast<uint8_t>(autotuneMode);

    serializeJson(doc, Serial);
    Serial.println();

    Serial.print("[Autotune] Heating PID -> Kp=");
    Serial.print(heatingPidCalculated ? heatingKp : currentParams.kp_heating, 4);
    Serial.print(", Ki=");
    Serial.print(heatingPidCalculated ? heatingKi : currentParams.ki_heating, 4);
    Serial.print(", Kd=");
    Serial.println(heatingPidCalculated ? heatingKd : currentParams.kd_heating, 4);

    if (coolingPidCalculated) {
        Serial.print("[Autotune] Cooling PID -> Kp=");
        Serial.print(coolingKp, 4);
        Serial.print(", Ki=");
        Serial.print(coolingKi, 4);
        Serial.print(", Kd=");
        Serial.println(coolingKd, 4);
    } else {
        Serial.println("[Autotune] Cooling PID unchanged");
        if (coolingReason.length() > 0) {
            comm.sendEvent(String("⚠️ Kjøle-autotune: ") + coolingReason);
        }
    }

    if (heatingPidCalculated) {
        comm.sendEvent("🔥 Heating PID parameters updated via autotune");
    } else {
        comm.sendEvent("🔥 Heating PID parameters unchanged");
    }
    if (coolingPidCalculated) {
        comm.sendEvent("❄️ Cooling PID parameters updated via autotune");
    }

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
