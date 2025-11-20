#include "pid_module.h"
#include "sensor_module.h"
#include "Arduino.h"
#include <ArduinoJson.h>

extern SensorModule sensors;

PIDModule::PIDModule()
  : pid(&Input, &Output, &Setpoint, 2.0, 0.5, 1.0, DIRECT),
    kp(2.0), ki(0.5), kd(1.0), maxOutputPercent(20.0),
    active(false), autotuneActive(false), autotuneStatus("idle"), autotunePhase("idle"), autotuneProgress(0),
    Input(0), Output(0), Setpoint(37.0),
    profileLength(0), currentProfileStep(0), profileStartMillis(0), profileActive(false),
    debugEnabled(false) {}

void PIDModule::begin(EEPROMManager &eepromManager) {
    eeprom = &eepromManager;

    float eKp, eKi, eKd;
    eeprom->loadPIDParams(eKp, eKi, eKd);
    setKp(eKp);
    setKi(eKi);
    setKd(eKd);

    float tTemp;
    eeprom->loadTargetTemp(tTemp);
    setTargetTemp(tTemp);

    pwm.begin();

    pid.SetSampleTime(100);
    pid.SetMode(MANUAL);

    applyOutputLimit();
}

void PIDModule::update(double currentTemp) {
    if (isFailsafeActive()) {
        stop();
        pwm.stopPWM();
        return;
    }

    Input = currentTemp;

    if (autotuneActive) {
        runAutotune();
        return;
    }

    if (profileActive) {
        updateProfile();
    }

    if (!active) {
        setPeltierOutput(0);
        return;
    }

    pid.Compute();
    applyPIDOutput();
}

void PIDModule::start() {
    clearFailsafe();
    pid.SetMode(AUTOMATIC);
    active = true;
}

void PIDModule::stop() {
    pid.SetMode(MANUAL);
    active = false;
    setPeltierOutput(0);
}

bool PIDModule::isActive() {
    return active;
}

// === Autotune ===
void PIDModule::startAutotune() {
    stop();
    backupKp = kp;
    backupKi = ki;
    backupKd = kd;

    autotuneStartMillis = millis();
    autotuneLastToggleMillis = autotuneStartMillis;
    autotuneDurationMs = 120000;           // 2 minutes test window
    autotuneToggleIntervalMs = 5000;       // toggle direction every 5 seconds
    autotuneProgress = 0;
    autotunePhase = "heating_step";
    autotuneCycles = 0;

    autotuneBaseline = sensors.getCoolingPlateTemp();

    // Use up to 30 % of the configured max output to excite the system safely
    float pwmMax = MAX_PWM * (maxOutputPercent / 100.0f);
    autotuneStepOutput = constrain(pwmMax * 0.3f, 80.0f, pwmMax);
    autotuneHighOutput = true;
    autotuneMaxTemp = autotuneBaseline;
    autotuneMinTemp = autotuneBaseline;

    setPeltierOutput(autotuneStepOutput);

    autotuneActive = true;
    autotuneStatus = "running";

    Serial.print("✅ Autotune started. Baseline=");
    Serial.print(autotuneBaseline, 2);
    Serial.print("°C, step PWM=");
    Serial.println(autotuneStepOutput, 0);
}

void PIDModule::runAutotune() {
    if (!autotuneActive) return;

    unsigned long now = millis();
    unsigned long elapsed = now - autotuneStartMillis;

    // Track temperature extremes
    float currentTemp = sensors.getCoolingPlateTemp();
    autotuneMaxTemp = max(autotuneMaxTemp, currentTemp);
    autotuneMinTemp = min(autotuneMinTemp, currentTemp);

    // Update progress
    autotuneProgress = (int)min(100UL, (elapsed * 100UL) / autotuneDurationMs);

    // Toggle output to create oscillation around the baseline
    if (now - autotuneLastToggleMillis >= autotuneToggleIntervalMs) {
        autotuneHighOutput = !autotuneHighOutput;
        autotunePhase = autotuneHighOutput ? "heating_step" : "cooling_step";
        float commanded = autotuneHighOutput ? autotuneStepOutput : -autotuneStepOutput;
        setPeltierOutput(commanded);
        autotuneLastToggleMillis = now;
        autotuneCycles++;

        if (debugEnabled) {
            Serial.print("[Autotune] Toggle → ");
            Serial.print(commanded);
            Serial.print(" (cycle ");
            Serial.print(autotuneCycles);
            Serial.println(")");
        }
    }

    // Finish after the test window
    if (elapsed >= autotuneDurationMs) {
        // Estimate coarse PID values from observed response
        float tempSwing = max(0.1f, autotuneMaxTemp - autotuneMinTemp);
        float stepPercent = (autotuneStepOutput / MAX_PWM) * 100.0f;
        float processGain = tempSwing / max(5.0f, stepPercent * 2.0f); // swing from +/- step
        float ultimateGain = 1.0f / max(0.05f, processGain);
        float oscillationPeriod = (float)(autotuneToggleIntervalMs * 2) / 1000.0f; // approx

        float newKp = 0.6f * ultimateGain;
        float newKi = (2.0f * newKp) / max(1.0f, oscillationPeriod);
        float newKd = newKp * oscillationPeriod * 0.125f;

        // Clamp to safe ranges
        newKp = constrain(newKp, 0.1f, 20.0f);
        newKi = constrain(newKi, 0.01f, 5.0f);
        newKd = constrain(newKd, 0.0f, 10.0f);

        setKp(newKp);
        setKi(newKi);
        setKd(newKd);
        applyOutputLimit();
        setPeltierOutput(0);

        autotuneActive = false;
        autotuneStatus = "complete";
        autotunePhase = "done";
        autotuneProgress = 100;

        if (eeprom) {
            eeprom->savePIDParams(newKp, newKi, newKd);
        }

        StaticJsonDocument<256> doc;
        JsonObject result = doc.createNestedObject("autotune_results");
        result["kp"] = newKp;
        result["ki"] = newKi;
        result["kd"] = newKd;
        result["temp_swing"] = tempSwing;
        result["step_percent"] = stepPercent;
        serializeJson(doc, Serial);
        Serial.println();

        Serial.print("✅ Autotune complete. New PID applied Kp=");
        Serial.print(newKp, 3);
        Serial.print(", Ki=");
        Serial.print(newKi, 3);
        Serial.print(", Kd=");
        Serial.println(newKd, 3);
    }
}

void PIDModule::abortAutotune() {
    if (!autotuneActive) return;

    setKp(backupKp);
    setKi(backupKi);
    setKd(backupKd);
    applyOutputLimit();

    autotuneActive = false;
    autotuneStatus = "aborted";
    autotunePhase = "aborted";
    autotuneProgress = 0;

    Serial.println("⚠️ Autotune aborted. Restored previous PID values.");
}

bool PIDModule::isAutotuneActive() {
    return autotuneActive;
}

const char* PIDModule::getAutotuneStatus() {
    return autotuneStatus;
}

const char* PIDModule::getAutotunePhase() {
    return autotunePhase;
}

int PIDModule::getAutotuneProgress() {
    return autotuneProgress;
}

// === PID parameters ===
void PIDModule::setKp(float value) { kp = value; pid.SetTunings(kp, ki, kd); }
void PIDModule::setKi(float value) { ki = value; pid.SetTunings(kp, ki, kd); }
void PIDModule::setKd(float value) { kd = value; pid.SetTunings(kp, ki, kd); }
void PIDModule::setTargetTemp(float value) { Setpoint = value; }

void PIDModule::setMaxOutputPercent(float percent) {
    if (percent < 0.0f) percent = 0.0f;
    if (percent > 100.0f) percent = 100.0f;
    maxOutputPercent = percent;
    applyOutputLimit();
}

float PIDModule::getKp() { return kp; }
float PIDModule::getKi() { return ki; }
float PIDModule::getKd() { return kd; }
float PIDModule::getTargetTemp() { return Setpoint; }
float PIDModule::getMaxOutputPercent() { return maxOutputPercent; }
float PIDModule::getOutput() { return Output; }
float PIDModule::getCurrentInput() { return Input; }
float PIDModule::getPwmOutput() { return Output; }

// === PID output ===
void PIDModule::applyOutputLimit() {
    int pwmMax = MAX_PWM * (maxOutputPercent / 100.0);
    pid.SetOutputLimits(-pwmMax, pwmMax);
}

void PIDModule::applyPIDOutput() {
    setPeltierOutput(Output);
}

void PIDModule::setPeltierOutput(double outVal) {
    int pwmVal = constrain((int)abs(outVal), 0, MAX_PWM);

    if (outVal > 0) {
        digitalWrite(8, LOW);
        digitalWrite(7, HIGH);
    } else if (outVal < 0) {
        digitalWrite(8, HIGH);
        digitalWrite(7, LOW);
    } else {
        digitalWrite(8, LOW);
        digitalWrite(7, LOW);
    }

    pwm.setDutyCycle(pwmVal);
}

void PIDModule::calculateZieglerNicholsParams() {
    kp = 3.6;
    ki = 0.72;
    kd = 0.9;

    pid.SetTunings(kp, ki, kd);
    applyOutputLimit();

    if (eeprom) {
        eeprom->savePIDParams(kp, ki, kd);
    }

    Serial.println("✅ Ziegler-Nichols params applied and saved.");
}

// === Profile ===
void PIDModule::loadProfile(ProfileStep* steps, int length) {
    if (length > 10) length = 10;

    for (int i = 0; i < length; i++) {
        profile[i] = steps[i];
    }

    profileLength = length;
    currentProfileStep = 0;
    profileActive = length > 0;
    profileStartMillis = millis();
}

bool PIDModule::isProfileActive() {
    return profileActive;
}

void PIDModule::updateProfile() {
    if (!profileActive) return;

    unsigned long elapsedMillis = millis() - profileStartMillis;
    float elapsedMinutes = elapsedMillis / 60000.0;

    if ((currentProfileStep + 1 < profileLength) &&
        (elapsedMinutes >= profile[currentProfileStep + 1].time)) {
        currentProfileStep++;
        setTargetTemp(profile[currentProfileStep].temp);
    }

    if (currentProfileStep + 1 >= profileLength &&
        elapsedMinutes >= profile[currentProfileStep].time) {
        profileActive = false;
    }
}

void PIDModule::enableDebug(bool enable) {
    debugEnabled = enable;
}

bool PIDModule::isDebugEnabled() {
    return debugEnabled;
}
