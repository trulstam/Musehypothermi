#include "pid_module.h"
#include "Arduino.h"

PIDModule::PIDModule()
  : pid(&Input, &Output, &Setpoint, 2.0, 0.5, 1.0, DIRECT),
    kp(2.0), ki(0.5), kd(1.0), maxOutputPercent(20.0),
    active(false), autotuneActive(false), autotuneStatus("idle"),
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
    autotuneActive = true;
    autotuneStatus = "running";

    backupKp = kp;
    backupKi = ki;
    backupKd = kd;

    autotuneStartMillis = millis();
    autotuneCycles = 0;

    Serial.println("✅ Autotune started");
}

void PIDModule::runAutotune() {
    if (!autotuneActive) return;

    unsigned long elapsed = millis() - autotuneStartMillis;

    if (elapsed > 10000) {
        calculateZieglerNicholsParams();

        autotuneActive = false;
        autotuneStatus = "complete";

        Serial.println("✅ Autotune complete. New PID values applied.");
    } else {
        if (debugEnabled && (elapsed % 1000 < 100)) {
            Serial.print("Autotune running: ");
            Serial.print(elapsed / 1000);
            Serial.println("s");
        }
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

    Serial.println("⚠️ Autotune aborted. Restored previous PID values.");
}

bool PIDModule::isAutotuneActive() {
    return autotuneActive;
}

const char* PIDModule::getAutotuneStatus() {
    return autotuneStatus;
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
