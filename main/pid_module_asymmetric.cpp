#include "pid_module_asymmetric.h"

#include "comm_api.h"
#include "sensor_module.h"

#include <Arduino.h>
#include <ArduinoJson.h>
#include <PID_v1.h>
#include <algorithm>
#include <math.h>

extern SensorModule sensors;
extern CommAPI comm;

int currentPwmOutput = 0;

namespace {
constexpr uint8_t kCoolingDirectionPin = 7;
constexpr uint8_t kHeatingDirectionPin = 8;
constexpr float kDefaultHeatingKp = 2.0f;
constexpr float kDefaultHeatingKi = 0.5f;
constexpr float kDefaultHeatingKd = 1.0f;

constexpr float kDefaultCoolingKp = 1.5f;
constexpr float kDefaultCoolingKi = 0.3f;
constexpr float kDefaultCoolingKd = 0.8f;

constexpr float kDefaultTargetTemp = 37.0f;
constexpr float kDefaultMaxOutputPercent = 20.0f;
constexpr float kStartupMaxOutputPercent = 20.0f;
constexpr unsigned long kStartupClampDurationMs = 60000UL;
constexpr float kDefaultDeadband = 0.5f;
constexpr float kDefaultSafetyMargin = 2.0f;
constexpr float kDefaultCoolingRate = 2.0f;
// The original controller smoothed 80% of the previous command into each new
// output. That heavy filtering effectively masked the PID tuning and produced
// similar oscillations regardless of the configured gains. Relax the
// smoothing so the PID output can directly shape the actuator behaviour while
// still avoiding abrupt jumps on the hardware.
constexpr double kOutputSmoothingFactor = 0.2;
constexpr unsigned long kSampleTimeMs = 100;

constexpr unsigned long kAutotuneSampleIntervalMs = 500;
constexpr unsigned long kAutotuneStabilityDurationMs = 10000;
constexpr float kAutotuneStabilityTolerance = 0.25f;
constexpr float kAutotuneSlopeTolerance = 0.05f;
constexpr float kAutotuneTargetDelta = 2.0f;
constexpr unsigned long kAutotuneMaxStepDurationMs = 90000;
constexpr unsigned long kAutotuneMaxSessionDurationMs = 600000;
constexpr float kAutotuneHeatingStepPercent = 30.0f;
constexpr float kAutotuneCoolingStepPercent = -20.0f;
constexpr float kAutotuneRecoveryTolerance = 0.3f;
constexpr unsigned long kAutotuneRecoveryHoldMs = 6000;
constexpr float kAutotuneMinDeltaForDeadTime = 0.05f;

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
      eeprom(nullptr),
      persistedHeatingLimit(kDefaultMaxOutputPercent),
      persistedCoolingLimit(kDefaultMaxOutputPercent),
      startupClampActive(false), startupClampNotified(false), startupClampEndMillis(0) {

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

    autotuneConfig.target = kDefaultTargetTemp;
    autotuneConfig.heatingStepPercent = kAutotuneHeatingStepPercent;
    autotuneConfig.coolingStepPercent = kAutotuneCoolingStepPercent;
    autotuneConfig.maxDurationMs = kAutotuneMaxSessionDurationMs;

    resetAutotuneSession();
}

void AsymmetricPIDModule::begin(EEPROMManager &eepromManager) {
    eeprom = &eepromManager;
    loadAsymmetricParams();

    pinMode(kCoolingDirectionPin, OUTPUT);
    pinMode(kHeatingDirectionPin, OUTPUT);
    digitalWrite(kCoolingDirectionPin, LOW);
    digitalWrite(kHeatingDirectionPin, LOW);

    // Configure both PID controllers
    coolingPID.SetSampleTime(kSampleTimeMs);
    heatingPID.SetSampleTime(kSampleTimeMs);

    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(MANUAL);

    pwm.begin();

    comm.sendEvent("🔧 Asymmetric PID controller ready");
}

void AsymmetricPIDModule::update(double /*currentTemp*/) {
    if (startupClampActive && millis() >= startupClampEndMillis) {
        startupClampActive = false;
        startupClampNotified = false;
        setOutputLimits(persistedCoolingLimit, persistedHeatingLimit, false);

        String message = "🔓 Startup output clamp released – heating ";
        message += String(persistedHeatingLimit, 1);
        message += "% / cooling ";
        message += String(persistedCoolingLimit, 1);
        message += "%";
        comm.sendEvent(message);
    }

    if (emergencyStop || isFailsafeActive()) {
        stop();
        return;
    }

    Input = sensors.getCoolingPlateTemp();
    unsigned long now = millis();

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

    publishFilterTelemetry("after_pid_compute", rawPIDOutput, rawPIDOutput);

    publishFilterTelemetry("before_safety_constraints", rawPIDOutput, rawPIDOutput);
    applySafetyConstraints();
    publishFilterTelemetry("after_safety_constraints", rawPIDOutput, rawPIDOutput);
    publishFilterTelemetry("before_rate_limit", rawPIDOutput, rawPIDOutput);
    applyRateLimiting();
    publishFilterTelemetry("after_rate_limit", rawPIDOutput, rawPIDOutput);
    publishFilterTelemetry("before_output_smoothing", rawPIDOutput, rawPIDOutput);
    applyOutputSmoothing();
    publishFilterTelemetry("after_output_smoothing", rawPIDOutput, finalOutput);

    double magnitude = fabs(finalOutput);
    int pwmValue = constrain(static_cast<int>(magnitude * MAX_PWM / 100.0), 0, MAX_PWM);

    if (finalOutput > 0.0) {
        digitalWrite(kHeatingDirectionPin, LOW);
        digitalWrite(kCoolingDirectionPin, HIGH);
    } else if (finalOutput < 0.0) {
        digitalWrite(kHeatingDirectionPin, HIGH);
        digitalWrite(kCoolingDirectionPin, LOW);
    } else {
        digitalWrite(kHeatingDirectionPin, LOW);
        digitalWrite(kCoolingDirectionPin, LOW);
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
    // Smooth output changes to prevent sudden jumps. Allow the filter to be
    // effectively disabled when the factor is zero so the PID output reaches
    // the actuator without additional attenuation.
    if (outputSmoothingFactor <= 0.0) {
        finalOutput = rawPIDOutput;
    } else if (outputSmoothingFactor >= 1.0) {
        finalOutput = lastOutput;
    } else {
        finalOutput = (outputSmoothingFactor * lastOutput) +
                      ((1.0 - outputSmoothingFactor) * rawPIDOutput);
    }

    lastOutput = finalOutput;
}

void AsymmetricPIDModule::publishFilterTelemetry(const char* stage, double rawValue, double finalValue) {
    if (!debugEnabled) {
        return;
    }

    String message = "[PID DEBUG] ";
    message += stage;
    message += " | mode=";
    message += coolingMode ? "cooling" : "heating";
    message += " | command=";
    double command = coolingMode ? coolingOutput : heatingOutput;
    message += String(command, 2);
    message += " | raw=";
    message += String(rawValue, 2);
    message += " | final=";
    message += String(finalValue, 2);
    comm.sendEvent(message);
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

    persistedCoolingLimit = constrainedCooling;
    persistedHeatingLimit = constrainedHeating;

    if (persistedHeatingLimit <= kStartupMaxOutputPercent &&
        persistedCoolingLimit <= kStartupMaxOutputPercent) {
        startupClampActive = false;
        startupClampEndMillis = 0;
    }

    float appliedCooling = constrainedCooling;
    float appliedHeating = constrainedHeating;

    if (startupClampActive) {
        float clampedCooling = std::min(appliedCooling, kStartupMaxOutputPercent);
        float clampedHeating = std::min(appliedHeating, kStartupMaxOutputPercent);
        bool clampApplied = (clampedCooling < appliedCooling) || (clampedHeating < appliedHeating);
        appliedCooling = clampedCooling;
        appliedHeating = clampedHeating;
        if (clampApplied && !startupClampNotified) {
            String message = "🔒 Startup output clamp active – applying ";
            message += String(appliedHeating, 1);
            message += "% / ";
            message += String(appliedCooling, 1);
            message += "% (heating/cooling)";
            comm.sendEvent(message);
            startupClampNotified = true;
        }
    } else {
        startupClampNotified = false;
    }

    currentParams.cooling_limit = -appliedCooling;
    currentParams.heating_limit = appliedHeating;

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

    coolingPID.SetTunings(kp, ki, kd);
    coolingPID.SetOutputLimits(currentParams.cooling_limit, 0.0);

    if (persist) {
        saveAsymmetricParams();
        String message = "🧊 Cooling PID parameters committed (kp=";
        message += String(kp, 4);
        message += ", ki=";
        message += String(ki, 4);
        message += ", kd=";
        message += String(kd, 4);
        message += ")";
        comm.sendEvent(message);
    }
}

void AsymmetricPIDModule::setHeatingPID(float kp, float ki, float kd, bool persist) {
    currentParams.kp_heating = kp;
    currentParams.ki_heating = ki;
    currentParams.kd_heating = kd;

    heatingPID.SetTunings(kp, ki, kd);
    heatingPID.SetOutputLimits(0.0, currentParams.heating_limit);

    if (persist) {
        saveAsymmetricParams();
        String message = "🔥 Heating PID parameters committed (kp=";
        message += String(kp, 4);
        message += ", ki=";
        message += String(ki, 4);
        message += ", kd=";
        message += String(kd, 4);
        message += ")";
        comm.sendEvent(message);
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

void AsymmetricPIDModule::resetAutotuneSession() {
    autotuneSession.phase = AutotunePhase::kIdle;
    autotuneSession.sessionStart = 0;
    autotuneSession.stateStart = 0;
    autotuneSession.lastSampleMillis = 0;
    autotuneSession.lastDerivativeMillis = 0;
    autotuneSession.lastDerivativeTemp = 0.0f;
    autotuneSession.currentSlope = 0.0f;
    autotuneSession.stabilityStart = 0;
    autotuneSession.target = autotuneConfig.target;
    autotuneSession.holdOutputPercent = 0.0f;
    autotuneSession.heatingCommandPercent = 0.0f;
    autotuneSession.coolingCommandPercent = 0.0f;
    autotuneSession.maxDurationMs = autotuneConfig.maxDurationMs;

    autotuneSession.heating.count = 0;
    autotuneSession.heating.startMillis = 0;
    autotuneSession.heating.stepPercent = autotuneConfig.heatingStepPercent;
    autotuneSession.heating.baseline = 0.0f;

    autotuneSession.cooling.count = 0;
    autotuneSession.cooling.startMillis = 0;
    autotuneSession.cooling.stepPercent = autotuneConfig.coolingStepPercent;
    autotuneSession.cooling.baseline = 0.0f;

    autotuneSession.recommendation.valid = false;
    autotuneSession.recommendation.heatingValid = false;
    autotuneSession.recommendation.coolingValid = false;
    autotuneSession.recommendation.heatingKp = currentParams.kp_heating;
    autotuneSession.recommendation.heatingKi = currentParams.ki_heating;
    autotuneSession.recommendation.heatingKd = currentParams.kd_heating;
    autotuneSession.recommendation.coolingKp = currentParams.kp_cooling;
    autotuneSession.recommendation.coolingKi = currentParams.ki_cooling;
    autotuneSession.recommendation.coolingKd = currentParams.kd_cooling;
    autotuneSession.recommendation.heatingProcessGain = 0.0f;
    autotuneSession.recommendation.heatingTimeConstant = 0.0f;
    autotuneSession.recommendation.heatingDeadTime = 0.0f;
    autotuneSession.recommendation.heatingInitialSlope = 0.0f;
    autotuneSession.recommendation.coolingProcessGain = 0.0f;
    autotuneSession.recommendation.coolingTimeConstant = 0.0f;
    autotuneSession.recommendation.coolingDeadTime = 0.0f;
    autotuneSession.recommendation.coolingInitialSlope = 0.0f;
}

void AsymmetricPIDModule::transitionAutotunePhase(AutotunePhase nextPhase, const char* statusMessage) {
    autotuneSession.phase = nextPhase;
    autotuneSession.stateStart = millis();
    autotuneSession.lastSampleMillis = 0;
    autotuneSession.stabilityStart = 0;
    autotuneStatusString = statusMessage;
}

void AsymmetricPIDModule::applyAutotuneOutput(float percent) {
    percent = constrain(percent, -100.0f, 100.0f);
    float magnitude = fabs(percent);
    int pwmValue = constrain(static_cast<int>(magnitude * MAX_PWM / 100.0f), 0, MAX_PWM);

    // Mirror the commanded percent into the PID bookkeeping so that
    // instrumentation (simulator, telemetry, etc.) observes the same
    // effective output even while the autotune bypasses the PID filters.
    rawPIDOutput = percent;
    finalOutput = percent;
    lastOutput = percent;

    if (percent > 0.0f) {
        digitalWrite(kHeatingDirectionPin, LOW);
        digitalWrite(kCoolingDirectionPin, HIGH);
    } else if (percent < 0.0f) {
        digitalWrite(kHeatingDirectionPin, HIGH);
        digitalWrite(kCoolingDirectionPin, LOW);
    } else {
        digitalWrite(kHeatingDirectionPin, LOW);
        digitalWrite(kCoolingDirectionPin, LOW);
    }

    pwm.setDutyCycle(pwmValue);
    currentPwmOutput = static_cast<int>(percent);
}

bool AsymmetricPIDModule::datasetFull(const AutotuneDataset& dataset) const {
    return dataset.count >= static_cast<int>(sizeof(dataset.samples) / sizeof(dataset.samples[0]));
}

void AsymmetricPIDModule::logAutotuneSample(AutotuneDataset& dataset, unsigned long now, float plateTemp,
                                            float coreTemp, float appliedOutputPercent) {
    if (datasetFull(dataset) || dataset.startMillis == 0) {
        return;
    }

    AutotuneSample sample;
    sample.timeMs = now - dataset.startMillis;
    sample.plateTemp = plateTemp;
    sample.coreTemp = coreTemp;
    sample.pwmPercent = appliedOutputPercent;

    dataset.samples[dataset.count] = sample;
    dataset.count = std::min(dataset.count + 1, static_cast<int>(sizeof(dataset.samples) / sizeof(dataset.samples[0])));
}

bool AsymmetricPIDModule::calculateProcessParameters(const AutotuneDataset& dataset, float& processGain,
                                                     float& timeConstant, float& deadTime, float& initialSlope) {
    processGain = 0.0f;
    timeConstant = 0.0f;
    deadTime = 0.0f;
    initialSlope = 0.0f;

    if (dataset.count < 5) {
        return false;
    }

    float initialTemp = dataset.samples[0].plateTemp;
    float finalTemp = dataset.samples[dataset.count - 1].plateTemp;
    float deltaTemp = finalTemp - initialTemp;
    if (fabs(deltaTemp) < 0.1f) {
        return false;
    }

    float stepFraction = dataset.stepPercent / 100.0f;
    if (fabs(stepFraction) < 0.01f) {
        return false;
    }

    processGain = deltaTemp / stepFraction;

    float targetTemp = initialTemp + 0.63f * deltaTemp;
    float t63 = dataset.samples[dataset.count - 1].timeMs / 1000.0f;
    for (int i = 1; i < dataset.count; ++i) {
        float prevTemp = dataset.samples[i - 1].plateTemp;
        float currentTemp = dataset.samples[i].plateTemp;
        bool reached = (deltaTemp > 0.0f && currentTemp >= targetTemp) ||
                       (deltaTemp < 0.0f && currentTemp <= targetTemp);
        if (reached) {
            float tPrev = dataset.samples[i - 1].timeMs / 1000.0f;
            float tCurr = dataset.samples[i].timeMs / 1000.0f;
            float denom = currentTemp - prevTemp;
            if (fabs(denom) < 1e-6f) {
                t63 = tCurr;
            } else {
                float ratio = (targetTemp - prevTemp) / denom;
                ratio = std::max(0.0f, std::min(1.0f, ratio));
                t63 = tPrev + (tCurr - tPrev) * ratio;
            }
            break;
        }
    }

    float threshold = std::max(kAutotuneMinDeltaForDeadTime, 0.05f * fabs(deltaTemp));
    for (int i = 1; i < dataset.count; ++i) {
        float deviation = fabs(dataset.samples[i].plateTemp - initialTemp);
        if (deviation >= threshold) {
            float y1 = dataset.samples[i - 1].plateTemp;
            float y2 = dataset.samples[i].plateTemp;
            float t1 = dataset.samples[i - 1].timeMs / 1000.0f;
            float t2 = dataset.samples[i].timeMs / 1000.0f;
            float dt = t2 - t1;
            if (dt <= 0.0f) {
                dt = 0.001f;
            }
            initialSlope = (y2 - y1) / dt;
            if (fabs(initialSlope) < 1e-6f) {
                initialSlope = (deltaTemp > 0.0f) ? 1e-6f : -1e-6f;
            }
            float yAtT = dataset.samples[i].plateTemp;
            float tAtT = t2;
            deadTime = tAtT - ((yAtT - initialTemp) / initialSlope);
            if (deadTime < 0.0f) {
                deadTime = 0.0f;
            }
            break;
        }
    }

    if (initialSlope == 0.0f) {
        float y1 = dataset.samples[dataset.count - 2].plateTemp;
        float y2 = dataset.samples[dataset.count - 1].plateTemp;
        float t1 = dataset.samples[dataset.count - 2].timeMs / 1000.0f;
        float t2 = dataset.samples[dataset.count - 1].timeMs / 1000.0f;
        float dt = std::max(0.001f, t2 - t1);
        initialSlope = (y2 - y1) / dt;
    }

    timeConstant = std::max(0.1f, t63 - deadTime);
    return true;
}

void AsymmetricPIDModule::computeRecommendedPid(float processGain, float timeConstant, float deadTime, bool heating,
                                                 float& kp, float& ki, float& kd) {
    float effectiveGain = std::max(0.01f, processGain);
    float effectiveTime = std::max(0.1f, timeConstant);
    float effectiveDead = std::max(0.05f, deadTime);

    float lambda = heating ? std::max(2.0f * effectiveDead, 0.5f * effectiveTime)
                           : std::max(3.0f * effectiveDead, 1.2f * effectiveTime);

    float baseKp = effectiveTime / (effectiveGain * (lambda + effectiveDead));
    if (heating) {
        baseKp *= 1.1f;
    } else {
        baseKp *= 0.8f;
    }

    float ti = effectiveTime + effectiveDead;
    float td = (effectiveDead * effectiveTime) / (effectiveTime + effectiveDead);

    kp = constrain(baseKp, 0.01f, 30.0f);
    ki = constrain(kp / std::max(0.1f, ti), 0.0f, 5.0f);
    kd = constrain(kp * td, 0.0f, 10.0f);
}

void AsymmetricPIDModule::appendSeries(JsonArray timestamps, JsonArray plateTemps, const AutotuneDataset& dataset,
                                       JsonArray* coreTemps) {
    if (dataset.count <= 0) {
        return;
    }

    int stride = std::max(1, dataset.count / 120);
    for (int i = 0; i < dataset.count; i += stride) {
        timestamps.add(static_cast<float>(dataset.samples[i].timeMs) / 1000.0f);
        plateTemps.add(dataset.samples[i].plateTemp);
        if (coreTemps) {
            coreTemps->add(dataset.samples[i].coreTemp);
        }
    }

    if ((dataset.count - 1) % stride != 0) {
        int idx = dataset.count - 1;
        timestamps.add(static_cast<float>(dataset.samples[idx].timeMs) / 1000.0f);
        plateTemps.add(dataset.samples[idx].plateTemp);
        if (coreTemps) {
            coreTemps->add(dataset.samples[idx].coreTemp);
        }
    }
}

void AsymmetricPIDModule::sendAutotuneResults(const AutotuneRecommendation& rec, const AutotuneDataset& heating,
                                              const AutotuneDataset& cooling) {
    DynamicJsonDocument doc(4096);
    JsonObject root = doc.createNestedObject("autotune_results");

    const char* status = "failed";
    if (rec.valid) {
        status = "complete";
    } else if (rec.heatingValid || rec.coolingValid) {
        status = "partial";
    }
    root["status"] = status;
    root["target"] = Setpoint;
    root["heating_step_percent"] = heating.stepPercent;
    root["cooling_step_percent"] = cooling.stepPercent;

    unsigned long stabilizationMs = 0;
    if (autotuneSession.sessionStart > 0 && heating.startMillis > autotuneSession.sessionStart) {
        stabilizationMs = heating.startMillis - autotuneSession.sessionStart;
    }
    unsigned long coolingEnd = 0;
    if (cooling.count > 0) {
        coolingEnd = cooling.startMillis + cooling.samples[cooling.count - 1].timeMs;
    } else if (heating.count > 0) {
        coolingEnd = heating.startMillis + heating.samples[heating.count - 1].timeMs;
    }
    if (coolingEnd > autotuneSession.sessionStart) {
        root["duration_ms"] = coolingEnd - autotuneSession.sessionStart;
    } else {
        root["duration_ms"] = 0;
    }
    root["stabilization_ms"] = stabilizationMs;

    JsonObject heatingObj = root.createNestedObject("heating");
    heatingObj["valid"] = rec.heatingValid;
    heatingObj["kp"] = rec.heatingKp;
    heatingObj["ki"] = rec.heatingKi;
    heatingObj["kd"] = rec.heatingKd;
    heatingObj["process_gain"] = rec.heatingProcessGain;
    heatingObj["time_constant"] = rec.heatingTimeConstant;
    heatingObj["dead_time"] = rec.heatingDeadTime;
    heatingObj["initial_slope"] = rec.heatingInitialSlope;
    heatingObj["baseline"] = heating.baseline;
    JsonArray heatingTimes = heatingObj.createNestedArray("timestamps");
    JsonArray heatingTemps = heatingObj.createNestedArray("plate_temperatures");
    JsonArray heatingCore = heatingObj.createNestedArray("core_temperatures");
    appendSeries(heatingTimes, heatingTemps, heating, &heatingCore);

    JsonObject coolingObj = root.createNestedObject("cooling");
    coolingObj["valid"] = rec.coolingValid;
    coolingObj["kp"] = rec.coolingKp;
    coolingObj["ki"] = rec.coolingKi;
    coolingObj["kd"] = rec.coolingKd;
    coolingObj["process_gain"] = rec.coolingProcessGain;
    coolingObj["time_constant"] = rec.coolingTimeConstant;
    coolingObj["dead_time"] = rec.coolingDeadTime;
    coolingObj["initial_slope"] = rec.coolingInitialSlope;
    coolingObj["baseline"] = cooling.baseline;
    JsonArray coolingTimes = coolingObj.createNestedArray("timestamps");
    JsonArray coolingTemps = coolingObj.createNestedArray("plate_temperatures");
    JsonArray coolingCore = coolingObj.createNestedArray("core_temperatures");
    appendSeries(coolingTimes, coolingTemps, cooling, &coolingCore);

    serializeJson(doc, Serial);
    Serial.println();
}

void AsymmetricPIDModule::finalizeAutotune() {
    applyAutotuneOutput(0.0f);

    AutotuneRecommendation& rec = autotuneSession.recommendation;
    float processGain = 0.0f;
    float timeConstant = 0.0f;
    float deadTime = 0.0f;
    float initialSlope = 0.0f;

    rec.heatingValid = calculateProcessParameters(autotuneSession.heating, processGain, timeConstant, deadTime, initialSlope);
    if (rec.heatingValid) {
        rec.heatingProcessGain = processGain;
        rec.heatingTimeConstant = timeConstant;
        rec.heatingDeadTime = deadTime;
        rec.heatingInitialSlope = initialSlope;
        computeRecommendedPid(processGain, timeConstant, deadTime, true, rec.heatingKp, rec.heatingKi, rec.heatingKd);
    }

    rec.coolingValid = calculateProcessParameters(autotuneSession.cooling, processGain, timeConstant, deadTime, initialSlope);
    if (rec.coolingValid) {
        rec.coolingProcessGain = processGain;
        rec.coolingTimeConstant = timeConstant;
        rec.coolingDeadTime = deadTime;
        rec.coolingInitialSlope = initialSlope;
        computeRecommendedPid(processGain, timeConstant, deadTime, false, rec.coolingKp, rec.coolingKi, rec.coolingKd);
    }

    rec.valid = rec.heatingValid && rec.coolingValid;

    autotuneActive = false;
    if (rec.valid) {
        autotuneStatusString = "done";
        comm.sendEvent("🎯 Asymmetric autotune completed");
    } else if (rec.heatingValid || rec.coolingValid) {
        autotuneStatusString = "partial";
        comm.sendEvent("⚠️ Autotune completed with partial data");
    } else {
        autotuneStatusString = "failed";
        comm.sendEvent("⛔ Autotune failed: insufficient response");
    }

    if (!rec.heatingValid && autotuneSession.heating.count == 0) {
        comm.sendEvent("⚠️ Heating step produced no samples");
    }
    if (!rec.coolingValid && autotuneSession.cooling.count == 0) {
        comm.sendEvent("⚠️ Cooling step produced no samples");
    }

    autotuneSession.phase = rec.valid ? AutotunePhase::kComplete : AutotunePhase::kFailed;

    sendAutotuneResults(rec, autotuneSession.heating, autotuneSession.cooling);
}

void AsymmetricPIDModule::startAutotune() {
    startAsymmetricAutotune();
}

void AsymmetricPIDModule::configureAutotune(float target, float heatingStepPercent, float coolingStepPercent,
                                            unsigned long maxDurationMs) {
    float safeTarget = constrain(target, 10.0f, 40.0f);
    autotuneConfig.target = safeTarget;
    setTargetTemp(safeTarget);

    float heatingLimit = currentParams.heating_limit;
    if (heatingLimit <= 0.0f) {
        heatingLimit = kDefaultMaxOutputPercent;
    }
    float safeHeatingStep = constrain(heatingStepPercent, 5.0f, heatingLimit);
    autotuneConfig.heatingStepPercent = safeHeatingStep;

    float coolingLimit = fabs(currentParams.cooling_limit);
    if (coolingLimit <= 0.0f) {
        coolingLimit = kDefaultMaxOutputPercent;
    }
    float safeCoolingMagnitude = constrain(fabs(coolingStepPercent), 5.0f, coolingLimit);
    autotuneConfig.coolingStepPercent = -safeCoolingMagnitude;

    unsigned long minDuration = 60UL * 1000UL;
    unsigned long maxDurationClamp = 60UL * 60UL * 1000UL;
    if (maxDurationMs < minDuration) {
        maxDurationMs = minDuration;
    } else if (maxDurationMs > maxDurationClamp) {
        maxDurationMs = maxDurationClamp;
    }
    autotuneConfig.maxDurationMs = maxDurationMs;
}

void AsymmetricPIDModule::startAsymmetricAutotune() {
    if (autotuneActive || emergencyStop || isFailsafeActive()) {
        if (isFailsafeActive()) {
            comm.sendEvent("⛔ Cannot start autotune while failsafe is active");
        }
        return;
    }

    float currentPlate = sensors.getCoolingPlateTemp();
    if (fabs(currentPlate - autotuneConfig.target) > 1.5f) {
        comm.sendEvent("⛔ Autotune start rejected: plate is not within ±1.5 °C of target");
        return;
    }

    float baselineOutput = static_cast<float>(finalOutput);
    float holdOutput = constrain(baselineOutput, currentParams.cooling_limit, currentParams.heating_limit);

    resetAutotuneSession();

    unsigned long now = millis();
    autotuneSession.sessionStart = now;
    autotuneSession.holdOutputPercent = holdOutput;
    autotuneSession.lastDerivativeMillis = now;
    autotuneSession.lastDerivativeTemp = currentPlate;

    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(MANUAL);
    active = false;
    applyAutotuneOutput(holdOutput);

    autotuneActive = true;
    transitionAutotunePhase(AutotunePhase::kStabilizing, "stabilizing");

    String message = "🎯 Asymmetric autotune: stabilizing at ";
    message += String(autotuneSession.target, 1);
    message += " °C (holding ";
    message += String(holdOutput, 1);
    message += " % PWM)";
    comm.sendEvent(message);
}

void AsymmetricPIDModule::runAsymmetricAutotune() {
    if (!autotuneActive) {
        return;
    }
    if (isFailsafeActive()) {
        abortAutotune();
        return;
    }

    unsigned long now = millis();
    float plateTemp = sensors.getCoolingPlateTemp();
    float coreTemp = sensors.getRectalTemp();

    if (autotuneSession.lastDerivativeMillis != 0) {
        unsigned long deltaMs = now - autotuneSession.lastDerivativeMillis;
        if (deltaMs > 0) {
            float deltaSeconds = static_cast<float>(deltaMs) / 1000.0f;
            autotuneSession.currentSlope = (plateTemp - autotuneSession.lastDerivativeTemp) / deltaSeconds;
        }
    }
    autotuneSession.lastDerivativeMillis = now;
    autotuneSession.lastDerivativeTemp = plateTemp;

    unsigned long maxDuration = autotuneSession.maxDurationMs > 0 ? autotuneSession.maxDurationMs
                                                                  : kAutotuneMaxSessionDurationMs;
    if (autotuneSession.sessionStart > 0 && (now - autotuneSession.sessionStart) > maxDuration) {
        autotuneActive = false;
        autotuneStatusString = "failed";
        comm.sendEvent("⛔ Autotune aborted: timeout");
        applyAutotuneOutput(0.0f);
        return;
    }

    switch (autotuneSession.phase) {
        case AutotunePhase::kStabilizing: {
            applyAutotuneOutput(autotuneSession.holdOutputPercent);
            bool withinBand = fabs(plateTemp - autotuneSession.target) <= kAutotuneStabilityTolerance;
            bool slopeStable = fabs(autotuneSession.currentSlope) <= kAutotuneSlopeTolerance;
            if (withinBand && slopeStable) {
                if (autotuneSession.stabilityStart == 0) {
                    autotuneSession.stabilityStart = now;
                } else if (now - autotuneSession.stabilityStart >= kAutotuneStabilityDurationMs) {
                    float hold = autotuneSession.holdOutputPercent;
                    float commanded = constrain(hold + autotuneSession.heating.stepPercent,
                                                currentParams.cooling_limit,
                                                currentParams.heating_limit);
                    float actualStep = commanded - hold;
                    if (actualStep < 5.0f) {
                        comm.sendEvent("⛔ Autotune aborted: insufficient heating headroom");
                        abortAutotune();
                        return;
                    }

                    autotuneSession.heating.stepPercent = actualStep;
                    autotuneSession.heatingCommandPercent = commanded;
                    autotuneSession.heating.startMillis = now;
                    autotuneSession.heating.count = 0;
                    autotuneSession.heating.baseline = plateTemp;
                    logAutotuneSample(autotuneSession.heating, now, plateTemp, coreTemp, hold);
                    transitionAutotunePhase(AutotunePhase::kHeatingStep, "heating_step");
                    autotuneSession.lastSampleMillis = now;

                    String stepMsg = "🔥 Autotune: applying heating step (";
                    stepMsg += String(hold, 1);
                    stepMsg += " % → ";
                    stepMsg += String(commanded, 1);
                    stepMsg += " %)";
                    comm.sendEvent(stepMsg);
                }
            } else {
                autotuneSession.stabilityStart = 0;
            }
            break;
        }
        case AutotunePhase::kHeatingStep: {
            applyAutotuneOutput(autotuneSession.heatingCommandPercent);
            if (autotuneSession.lastSampleMillis == 0 ||
                now - autotuneSession.lastSampleMillis >= kAutotuneSampleIntervalMs) {
                logAutotuneSample(autotuneSession.heating, now, plateTemp, coreTemp,
                                  autotuneSession.heatingCommandPercent);
                autotuneSession.lastSampleMillis = now;
            }

            bool reachedDelta = fabs(plateTemp - autotuneSession.heating.baseline) >= kAutotuneTargetDelta;
            bool timeout = (now - autotuneSession.stateStart) >= kAutotuneMaxStepDurationMs;
            if (datasetFull(autotuneSession.heating) || reachedDelta || timeout) {
                transitionAutotunePhase(AutotunePhase::kHeatingRecover, "heating_recover");
                applyAutotuneOutput(autotuneSession.holdOutputPercent);
                comm.sendEvent("♨️ Heating step recorded – returning to hold output");
            }
            break;
        }
        case AutotunePhase::kHeatingRecover: {
            applyAutotuneOutput(autotuneSession.holdOutputPercent);
            bool withinBand = fabs(plateTemp - autotuneSession.target) <= kAutotuneRecoveryTolerance;
            bool slopeStable = fabs(autotuneSession.currentSlope) <= kAutotuneSlopeTolerance;
            if (withinBand && slopeStable) {
                if (autotuneSession.stabilityStart == 0) {
                    autotuneSession.stabilityStart = now;
                } else if (now - autotuneSession.stabilityStart >= kAutotuneRecoveryHoldMs) {
                    float hold = autotuneSession.holdOutputPercent;
                    float commanded = constrain(hold + autotuneSession.cooling.stepPercent,
                                                currentParams.cooling_limit,
                                                currentParams.heating_limit);
                    float actualStep = commanded - hold;
                    if (actualStep > -5.0f) {
                        comm.sendEvent("⛔ Autotune aborted: insufficient cooling headroom");
                        abortAutotune();
                        return;
                    }

                    autotuneSession.cooling.stepPercent = actualStep;
                    autotuneSession.coolingCommandPercent = commanded;
                    autotuneSession.cooling.startMillis = now;
                    autotuneSession.cooling.count = 0;
                    autotuneSession.cooling.baseline = plateTemp;
                    logAutotuneSample(autotuneSession.cooling, now, plateTemp, coreTemp, hold);
                    transitionAutotunePhase(AutotunePhase::kCoolingStep, "cooling_step");
                    autotuneSession.lastSampleMillis = now;

                    String coolMsg = "❄️ Autotune: applying cooling step (";
                    coolMsg += String(hold, 1);
                    coolMsg += " % → ";
                    coolMsg += String(commanded, 1);
                    coolMsg += " %)";
                    comm.sendEvent(coolMsg);
                }
            } else {
                autotuneSession.stabilityStart = 0;
            }
            break;
        }
        case AutotunePhase::kCoolingStep: {
            applyAutotuneOutput(autotuneSession.coolingCommandPercent);
            if (autotuneSession.lastSampleMillis == 0 ||
                now - autotuneSession.lastSampleMillis >= kAutotuneSampleIntervalMs) {
                logAutotuneSample(autotuneSession.cooling, now, plateTemp, coreTemp,
                                  autotuneSession.coolingCommandPercent);
                autotuneSession.lastSampleMillis = now;
            }

            bool reachedDelta = fabs(plateTemp - autotuneSession.cooling.baseline) >= kAutotuneTargetDelta;
            bool timeout = (now - autotuneSession.stateStart) >= kAutotuneMaxStepDurationMs;
            if (datasetFull(autotuneSession.cooling) || reachedDelta || timeout) {
                transitionAutotunePhase(AutotunePhase::kCoolingRecover, "cooling_recover");
                applyAutotuneOutput(autotuneSession.holdOutputPercent);
                comm.sendEvent("❄️ Cooling step recorded – monitoring hold recovery");
            }
            break;
        }
        case AutotunePhase::kCoolingRecover: {
            applyAutotuneOutput(autotuneSession.holdOutputPercent);
            bool withinBand = fabs(plateTemp - autotuneSession.target) <= kAutotuneRecoveryTolerance;
            bool slopeStable = fabs(autotuneSession.currentSlope) <= kAutotuneSlopeTolerance;
            if (withinBand && slopeStable) {
                if (autotuneSession.stabilityStart == 0) {
                    autotuneSession.stabilityStart = now;
                } else if (now - autotuneSession.stabilityStart >= kAutotuneRecoveryHoldMs) {
                    finalizeAutotune();
                }
            } else {
                autotuneSession.stabilityStart = 0;
            }
            break;
        }
        case AutotunePhase::kComplete:
        case AutotunePhase::kFailed:
        case AutotunePhase::kIdle:
        default:
            applyAutotuneOutput(0.0f);
            break;
    }
}

void AsymmetricPIDModule::performCoolingAutotune() {}

void AsymmetricPIDModule::performHeatingAutotune() {}

void AsymmetricPIDModule::abortAutotune() {
    applyAutotuneOutput(0.0f);
    autotuneActive = false;
    autotuneStatusString = "aborted";
    autotuneSession.phase = AutotunePhase::kFailed;
    comm.sendEvent("⛔ Asymmetric autotune aborted");
}

bool AsymmetricPIDModule::hasAutotuneRecommendations() const {
    return autotuneSession.recommendation.valid;
}

bool AsymmetricPIDModule::applyAutotuneRecommendations() {
    if (!autotuneSession.recommendation.valid) {
        return false;
    }

    setHeatingPID(autotuneSession.recommendation.heatingKp,
                  autotuneSession.recommendation.heatingKi,
                  autotuneSession.recommendation.heatingKd,
                  false);
    setCoolingPID(autotuneSession.recommendation.coolingKp,
                  autotuneSession.recommendation.coolingKi,
                  autotuneSession.recommendation.coolingKd,
                  false);
    saveAsymmetricParams();
    comm.sendEvent("💾 Asymmetric autotune parameters committed");

    autotuneSession.recommendation.valid = false;
    return true;
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
        persistedHeatingLimit,
        persistedCoolingLimit,
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
            comm.sendEvent("⚠️ EEPROM heating PID invalid – restored defaults");
        }

        eeprom->loadCoolingPIDParams(coolingKp, coolingKi, coolingKd);
        if (shouldRestorePID(coolingKp, coolingKi, coolingKd)) {
            coolingKp = kDefaultCoolingKp;
            coolingKi = kDefaultCoolingKi;
            coolingKd = kDefaultCoolingKd;
            eeprom->saveCoolingPIDParams(coolingKp, coolingKi, coolingKd);
            restoredDefaults = true;
            comm.sendEvent("⚠️ EEPROM cooling PID invalid – restored defaults");
        }

        eeprom->loadTargetTemp(target);
        if (shouldRestoreTarget(target)) {
            target = kDefaultTargetTemp;
            eeprom->saveTargetTemp(target);
            restoredDefaults = true;
            comm.sendEvent("⚠️ EEPROM target temperature invalid – restored to 37°C");
        }

        eeprom->loadHeatingMaxOutput(heatingLimit);
        if (shouldRestoreMaxOutput(heatingLimit)) {
            heatingLimit = kDefaultMaxOutputPercent;
            eeprom->saveHeatingMaxOutput(heatingLimit);
            restoredDefaults = true;
            comm.sendEvent("⚠️ EEPROM heating max output invalid – restored to 20%");
        }

        eeprom->loadCoolingMaxOutput(coolingLimit);
        if (shouldRestoreMaxOutput(coolingLimit)) {
            coolingLimit = kDefaultMaxOutputPercent;
            eeprom->saveCoolingMaxOutput(coolingLimit);
            restoredDefaults = true;
            comm.sendEvent("⚠️ EEPROM cooling max output invalid – restored to 20%");
        }

        eeprom->loadCoolingRateLimit(storedRate);
        if (shouldRestoreCoolingRate(storedRate)) {
            storedRate = kDefaultCoolingRate;
            eeprom->saveCoolingRateLimit(storedRate);
            restoredDefaults = true;
            comm.sendEvent("⚠️ EEPROM cooling rate limit invalid – restored to default");
        }

        eeprom->loadDeadband(storedDeadband);
        if (shouldRestoreDeadband(storedDeadband)) {
            storedDeadband = kDefaultDeadband;
            eeprom->saveDeadband(storedDeadband);
            restoredDefaults = true;
            comm.sendEvent("⚠️ EEPROM deadband invalid – restored to default");
        }

        eeprom->loadSafetyMargin(storedMargin);
        if (shouldRestoreSafetyMargin(storedMargin)) {
            storedMargin = kDefaultSafetyMargin;
            eeprom->saveSafetyMargin(storedMargin);
            restoredDefaults = true;
            comm.sendEvent("⚠️ EEPROM safety margin invalid – restored to default");
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
    persistedHeatingLimit = heatingLimit;
    persistedCoolingLimit = coolingLimit;
    startupClampActive = (persistedHeatingLimit > kStartupMaxOutputPercent) ||
                         (persistedCoolingLimit > kStartupMaxOutputPercent);
    startupClampNotified = false;
    startupClampEndMillis = startupClampActive ? millis() + kStartupClampDurationMs : 0;

    setOutputLimits(persistedCoolingLimit, persistedHeatingLimit, false);
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
