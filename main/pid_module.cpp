// Musehypothermi PID Module - Thread 5
// File: pid_module.cpp

#include "pid_module.h"
#include "comm_api.h"
#include "sensor_module.h"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <PID_v1.h>

extern SensorModule sensors;
extern CommAPI comm;

// Global PWM tracker for simulation
int currentPwmOutput = 0;

PIDModule::PIDModule()
  : pid(&Input, &Output, &Setpoint, 2.0, 0.5, 1.0, DIRECT),
    kp(2.0), ki(0.5), kd(1.0), maxOutputPercent(20.0),
    active(false), autotuneActive(false), autotuneStatus("idle"),
    Input(0), Output(0), Setpoint(37.0),
    profileLength(0), currentProfileStep(0), profileStartMillis(0), profileActive(false),
    debugEnabled(false), actualPlateTarget(37.0) {}

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

    Input = sensors.getCoolingPlateTemp();

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
    Output = 0;
    setPeltierOutput(0);
}

bool PIDModule::isActive() {
    return active;
}

void PIDModule::startAutotune() {
    autotuneActive = true;
    autotuneStatus = "running";
    autotuneStartMillis = millis();
    autotuneLogIndex = 0;
    
    // Bruk høyere PWM for bedre signal-til-støy ratio
    setPeltierOutput(500);  // 500/2399 ≈ 21% PWM
    comm.sendEvent("Autotune started: step response (21% PWM)");
}

void PIDModule::runAutotune() {
    if (!autotuneActive) return;

    unsigned long now = millis();
    unsigned long elapsed = now - autotuneStartMillis;
    
    // Sample every 500ms (mer stabil enn 100ms)
    static unsigned long lastSample = 0;
    if (now - lastSample < 500) return;
    lastSample = now;

    if (autotuneLogIndex < AUTOTUNE_LOG_SIZE) {
        float temp = sensors.getCoolingPlateTemp();

        autotuneTimestamps[autotuneLogIndex] = elapsed;
        autotuneTemperatures[autotuneLogIndex] = temp;
        autotuneLogIndex++;

        // Send data til GUI (kun hver 5. sample for å redusere trafikk)
        if (autotuneLogIndex % 5 == 0) {
            StaticJsonDocument<128> doc;
            doc["autotune_time"] = elapsed;
            doc["autotune_temp"] = temp;
            doc["autotune_progress"] = (autotuneLogIndex * 100) / AUTOTUNE_LOG_SIZE;
            serializeJson(doc, Serial);
            Serial.println();
        }
    } else {
        // Autotune complete
        autotuneActive = false;
        setPeltierOutput(0);
        autotuneStatus = "done";
        
        calculateAutotuneParams();
        comm.sendEvent("Autotune complete: new PID parameters calculated");
    }
    
    // Safety timeout (max 5 minutter)
    if (elapsed > 300000) {  // 5 min timeout
        abortAutotune();
        comm.sendEvent("Autotune aborted: timeout reached");
    }
}

void PIDModule::calculateAutotuneParams() {
    if (autotuneLogIndex < 50) {
        Serial.println("Not enough autotune data for calculation");
        return;
    }

    // Find initial and final temperatures
    float initialTemp = autotuneTemperatures[0];
    float finalTemp = autotuneTemperatures[autotuneLogIndex - 1];
    float deltaTemp = finalTemp - initialTemp;
    
    // If no significant temperature change, use default parameters
    if (abs(deltaTemp) < 0.1) {
        Serial.println("No significant temperature change during autotune");
        setKp(2.0);
        setKi(0.5);
        setKd(1.0);
        return;
    }
    
    // Step response analysis (simplified Ziegler-Nichols)
    float stepSize = 500.0 / 2399.0; // PWM step as fraction
    float processGain = deltaTemp / stepSize; // K_process
    
    // Find approximate time constants
    float t63 = 0; // Time to reach 63% of final value
    float targetTemp = initialTemp + 0.63 * deltaTemp;
    
    // Find t63 from data
    for (int i = 1; i < autotuneLogIndex; i++) {
        if ((deltaTemp > 0 && autotuneTemperatures[i] >= targetTemp) ||
            (deltaTemp < 0 && autotuneTemperatures[i] <= targetTemp)) {
            t63 = autotuneTimestamps[i] / 1000.0; // Convert to seconds
            break;
        }
    }
    
    if (t63 == 0) t63 = autotuneTimestamps[autotuneLogIndex - 1] / 2000.0;
    
    // Find dead time (simplified - assume minimal for this system)
    float deadTime = 1.0; // seconds (estimated)
    
    // Ziegler-Nichols PID tuning for step response
    // For temperature control, use conservative settings
    float timeConstant = t63 / 0.63;
    
    float newKp = 1.2 / (processGain * (deadTime / timeConstant));
    float newKi = newKp / (2.0 * deadTime);
    float newKd = newKp * deadTime * 0.5;
    
    // Apply reasonable bounds for temperature control
    newKp = constrain(newKp, 0.1, 20.0);
    newKi = constrain(newKi, 0.01, 5.0);
    newKd = constrain(newKd, 0.01, 10.0);
    
    // Update PID parameters
    setKp(newKp);
    setKi(newKi);
    setKd(newKd);
    
    // Save to EEPROM
    eeprom->savePIDParams(newKp, newKi, newKd);
    
    // Send results to GUI
    StaticJsonDocument<256> doc;
    doc["autotune_results"]["kp"] = newKp;
    doc["autotune_results"]["ki"] = newKi;
    doc["autotune_results"]["kd"] = newKd;
    doc["autotune_results"]["process_gain"] = processGain;
    doc["autotune_results"]["time_constant"] = timeConstant;
    serializeJson(doc, Serial);
    Serial.println();
    
    Serial.print("Autotune complete - New PID: Kp=");
    Serial.print(newKp);
    Serial.print(", Ki=");
    Serial.print(newKi);
    Serial.print(", Kd=");
    Serial.println(newKd);
}

void PIDModule::abortAutotune() {
    autotuneActive = false;
    autotuneStatus = "aborted";
    setPeltierOutput(0);
    comm.sendEvent("Autotune aborted");
}

bool PIDModule::isAutotuneActive() { return autotuneActive; }
const char* PIDModule::getAutotuneStatus() { return autotuneStatus; }

void PIDModule::setKp(float value) { kp = value; pid.SetTunings(kp, ki, kd); }
void PIDModule::setKi(float value) { ki = value; pid.SetTunings(kp, ki, kd); }
void PIDModule::setKd(float value) { kd = value; pid.SetTunings(kp, ki, kd); }
void PIDModule::setTargetTemp(float value) { Setpoint = value; actualPlateTarget = value; }

void PIDModule::setMaxOutputPercent(float percent) {
    if (percent < 0.0f) percent = 0.0f;
    if (percent > 100.0f) percent = 100.0f;
    maxOutputPercent = percent;
    applyOutputLimit();

    comm.sendStatus("pid_output_limit", maxOutputPercent);
}

float PIDModule::getKp() { return kp; }
float PIDModule::getKi() { return ki; }
float PIDModule::getKd() { return kd; }
float PIDModule::getTargetTemp() { return Setpoint; }
float PIDModule::getActivePlateTarget() { return actualPlateTarget; }
float PIDModule::getMaxOutputPercent() { return maxOutputPercent; }
float PIDModule::getOutput() { return Output; }
float PIDModule::getCurrentInput() { return Input; }
float PIDModule::getPwmOutput() { return Output; }

void PIDModule::applyOutputLimit() {
    int pwmMax = MAX_PWM * (maxOutputPercent / 100.0);
    pid.SetOutputLimits(-pwmMax, pwmMax);
    Output = constrain(Output, -pwmMax, pwmMax);
}

void PIDModule::applyPIDOutput() {
    setPeltierOutput(Output);
}

void PIDModule::setPeltierOutput(double outVal) {
    int pwmVal = constrain((int)abs(outVal), 0, MAX_PWM);
    currentPwmOutput = (outVal < 0) ? -pwmVal : pwmVal;  // Lagre med fortegn
    
    comm.sendStatus("pwm_applied", pwmVal);

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

void PIDModule::loadProfile(ProfileStep* steps, int length) {}
bool PIDModule::isProfileActive() { return false; }
void PIDModule::updateProfile() {}

void PIDModule::enableDebug(bool enable) { debugEnabled = enable; }
bool PIDModule::isDebugEnabled() { return debugEnabled; }