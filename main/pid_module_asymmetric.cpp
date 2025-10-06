// Enhanced PID Module Implementation with Asymmetric Control
// File: pid_module_asymmetric.cpp

#include "pid_module_asymmetric.h"
#include "comm_api.h"
#include "sensor_module.h"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <PID_v1.h>

extern SensorModule sensors;
extern CommAPI comm;

// Global PWM tracker for simulation
int currentPwmOutput = 0;

AsymmetricPIDModule::AsymmetricPIDModule()
    : coolingPID(&Input, &coolingOutput, &Setpoint, 2.0, 0.5, 1.0, REVERSE),
      heatingPID(&Input, &heatingOutput, &Setpoint, 1.5, 0.3, 0.8, DIRECT),
      Input(0), coolingOutput(0), heatingOutput(0), Setpoint(37.0),
      active(false), autotuneActive(false), 
      debugEnabled(false),
      coolingMode(false), emergencyStop(false),
      maxCoolingRate(2.0), outputSmoothingFactor(0.8),
      lastOutput(0), rawPIDOutput(0), finalOutput(0),
      lastTemperature(0), lastUpdateTime(0), temperatureRate(0),
      autotuneStatusString("idle") {
    
    // Initialize default parameters
    currentParams.kp_cooling = 2.0;
    currentParams.ki_cooling = 0.5;
    currentParams.kd_cooling = 1.0;
    currentParams.kp_heating = 1.5;
    currentParams.ki_heating = 0.3;
    currentParams.kd_heating = 0.8;
    currentParams.deadband = 0.5;
    currentParams.safety_margin = 2.0;
    currentParams.cooling_limit = -20.0;
    currentParams.heating_limit = 20.0;
}
void AsymmetricPIDModule::begin(EEPROMManager &eepromManager) {
    eeprom = &eepromManager;
    loadAsymmetricParams();
    
    // Configure both PID controllers
    coolingPID.SetSampleTime(100);
    heatingPID.SetSampleTime(100);
    
    coolingPID.SetOutputLimits(currentParams.cooling_limit, 0);
    heatingPID.SetOutputLimits(0, currentParams.heating_limit);
    
    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(MANUAL);
    
    pwm.begin();
    
    comm.sendEvent("🔧 Asymmetric PID controller initialized");
}

void AsymmetricPIDModule::update(double currentTemp) {
    if (emergencyStop || isFailsafeActive()) {
        stop();
        return;
    }
    
    Input = sensors.getCoolingPlateTemp();
    unsigned long now = millis();
    
    if (!active) {
        finalOutput = 0;
        pwm.setDutyCycle(0);
        return;
    }
    
    // Calculate temperature rate of change for safety monitoring
    if (lastUpdateTime > 0) {
        float deltaTime = (now - lastUpdateTime) / 1000.0;
        if (deltaTime > 0) {
            temperatureRate = (Input - lastTemperature) / deltaTime;
        }
    }
    lastTemperature = Input;
    lastUpdateTime = now;
    
    // Safety check - emergency stop if cooling too fast
    if (temperatureRate < -maxCoolingRate) {
        setEmergencyStop(true);
        comm.sendEvent("🚨 EMERGENCY: Cooling rate exceeded safety limit!");
        return;
    }
    
    double error = Setpoint - Input;
    
    // Check safety limits before proceeding
    if (!checkSafetyLimits(Input, Setpoint)) {
        return;
    }
    
    // Update PID mode based on error and current state
    updatePIDMode(error);
    
    // Compute PID output
    if (coolingMode) {
        coolingPID.Compute();
        rawPIDOutput = coolingOutput;
    } else {
        heatingPID.Compute();
        rawPIDOutput = heatingOutput;
    }
    
    // Apply safety constraints and smoothing
    applySafetyConstraints();
    applyOutputSmoothing();
    
    // Apply final output
    int pwmValue = constrain(abs(finalOutput) * 2399.0 / 100.0, 0, 2399);
    
    if (finalOutput < 0) {
        // Cooling mode
        digitalWrite(8, HIGH);  // Cooling direction
        digitalWrite(7, LOW);
    } else if (finalOutput > 0) {
        // Heating mode  
        digitalWrite(8, LOW);   // Heating direction
        digitalWrite(7, HIGH);
    } else {
        // Off
        digitalWrite(8, LOW);
        digitalWrite(7, LOW);
    }
    
    pwm.setDutyCycle(pwmValue);
    currentPwmOutput = finalOutput; // Update global tracker
}

void AsymmetricPIDModule::updatePIDMode(double error) {
    bool shouldCool = error < -currentParams.deadband;
    bool shouldHeat = error > currentParams.deadband;
    
    // Hysteresis logic to prevent oscillation between modes
    if (shouldCool && !coolingMode) {
        switchToCoolingPID();
    } else if (shouldHeat && coolingMode) {
        switchToHeatingPID();
    }
    // Stay in current mode if within deadband
}

void AsymmetricPIDModule::switchToCoolingPID() {
    coolingMode = true;
    heatingPID.SetMode(MANUAL);
    coolingPID.SetMode(AUTOMATIC);
    
    // Set conservative cooling parameters
    coolingPID.SetTunings(currentParams.kp_cooling, 
                         currentParams.ki_cooling, 
                         currentParams.kd_cooling);
    
    comm.sendEvent("❄️ Switched to COOLING mode");
}

void AsymmetricPIDModule::switchToHeatingPID() {
    coolingMode = false;
    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(AUTOMATIC);
    
    // Set more aggressive heating parameters
    heatingPID.SetTunings(currentParams.kp_heating, 
                         currentParams.ki_heating, 
                         currentParams.kd_heating);
    
    comm.sendEvent("🔥 Switched to HEATING mode");
}

bool AsymmetricPIDModule::checkSafetyLimits(double currentTemp, double targetTemp) {
    // Critical safety check: Don't cool below safety margin
    if (coolingMode && (currentTemp <= targetTemp - currentParams.safety_margin)) {
        setEmergencyStop(true);
        comm.sendEvent("🚨 SAFETY: Temperature below safety margin!");
        return false;
    }
    
    // Check for reasonable temperature range
    if (currentTemp < 10.0 || currentTemp > 45.0) {
        setEmergencyStop(true);
        comm.sendEvent("🚨 SAFETY: Temperature out of safe range!");
        return false;
    }
    
    return true;
}

void AsymmetricPIDModule::applySafetyConstraints() {
    // Additional output limiting based on current conditions
    if (coolingMode) {
        // More conservative cooling near target
        double distanceToTarget = abs(Input - Setpoint);
        if (distanceToTarget < 2.0) {
            // Reduce cooling power when close to target
            float reductionFactor = distanceToTarget / 2.0;
            rawPIDOutput *= reductionFactor;
        }
        
        // Never exceed cooling limit
        rawPIDOutput = max(rawPIDOutput, currentParams.cooling_limit);
    } else {
        // Heating constraints
        rawPIDOutput = min(rawPIDOutput, currentParams.heating_limit);
    }
}

void AsymmetricPIDModule::applyOutputSmoothing() {
    // Smooth output changes to prevent sudden jumps
    finalOutput = (outputSmoothingFactor * lastOutput) + 
                  ((1.0 - outputSmoothingFactor) * rawPIDOutput);
    lastOutput = finalOutput;
}

// Compatibility methods
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
    return coolingMode ? abs(currentParams.cooling_limit) : currentParams.heating_limit;
}

const char* AsymmetricPIDModule::getAutotuneStatus() {
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

void AsymmetricPIDModule::setMaxOutputPercent(float percent) {
    currentParams.cooling_limit = -percent;
    currentParams.heating_limit = percent;
    coolingPID.SetOutputLimits(-percent, 0);
    heatingPID.SetOutputLimits(0, percent);
}

void AsymmetricPIDModule::setCoolingPID(float kp, float ki, float kd) {
    currentParams.kp_cooling = kp;
    currentParams.ki_cooling = ki;
    currentParams.kd_cooling = kd;
    
    if (coolingMode) {
        coolingPID.SetTunings(kp, ki, kd);
    }
    
    saveAsymmetricParams();
    comm.sendEvent("❄️ Cooling PID parameters updated");
}

void AsymmetricPIDModule::setHeatingPID(float kp, float ki, float kd) {
    currentParams.kp_heating = kp;
    currentParams.ki_heating = ki;
    currentParams.kd_heating = kd;
    
    if (!coolingMode) {
        heatingPID.SetTunings(kp, ki, kd);
    }
    
    saveAsymmetricParams();
    comm.sendEvent("🔥 Heating PID parameters updated");
}

void AsymmetricPIDModule::setEmergencyStop(bool enabled) {
    emergencyStop = enabled;
    if (enabled) {
        finalOutput = 0;
        pwm.setDutyCycle(0);
        digitalWrite(8, LOW);
        digitalWrite(7, LOW);
        comm.sendEvent("🚨 EMERGENCY STOP ACTIVATED");
    } else {
        comm.sendEvent("✅ Emergency stop cleared");
    }
}

void AsymmetricPIDModule::setCoolingRateLimit(float maxRate) {
    maxCoolingRate = maxRate;
    comm.sendEvent("⚠️ Cooling rate limit set to " + String(maxRate) + "°C/s");
}

void AsymmetricPIDModule::setSafetyParams(float deadband, float safetyMargin) {
    currentParams.deadband = deadband;
    currentParams.safety_margin = safetyMargin;
    saveAsymmetricParams();
}

void AsymmetricPIDModule::startAutotune() {
    startAsymmetricAutotune();
}

void AsymmetricPIDModule::startAsymmetricAutotune() {
    if (autotuneActive) return;
    
    autotuneActive = true;
    autotuneStatusString = "running";
    comm.sendEvent("🎯 Starting asymmetric autotune (cooling first)");
    
    // Start with cooling autotune (more critical)
    performCoolingAutotune();
}

void AsymmetricPIDModule::runAsymmetricAutotune() {
    if (!autotuneActive) return;
    
    // Simple autotune placeholder - implement actual logic later
    static unsigned long autotuneStart = millis();
    if (millis() - autotuneStart > 30000) { // 30 second test
        autotuneActive = false;
        autotuneStatusString = "done";
        comm.sendEvent("🎯 Asymmetric autotune completed (placeholder)");
    }
}

void AsymmetricPIDModule::performCoolingAutotune() {
    // Conservative cooling step test
    comm.sendEvent("❄️ Performing cooling autotune...");
    // Implementation would follow similar pattern to original autotune
    // but with safety constraints and conservative parameter calculation
}

void AsymmetricPIDModule::abortAutotune() {
    autotuneActive = false;
    autotuneStatusString = "aborted";
    comm.sendEvent("⛔ Asymmetric autotune aborted");
}

void AsymmetricPIDModule::saveAsymmetricParams() {
    // Save both heating and cooling parameters to EEPROM
    // Basic implementation - store in existing EEPROM slots for now
    if (eeprom) {
        eeprom->savePIDParams(currentParams.kp_cooling, 
                             currentParams.ki_cooling, 
                             currentParams.kd_cooling);
    }
}

void AsymmetricPIDModule::loadAsymmetricParams() {
    // Load parameters from EEPROM or use defaults
    // For now, use the defaults set in constructor
    if (eeprom) {
        float kp, ki, kd;
        eeprom->loadPIDParams(kp, ki, kd);
        currentParams.kp_cooling = kp;
        currentParams.ki_cooling = ki;
        currentParams.kd_cooling = kd;
    }
}

// Debug methods
void AsymmetricPIDModule::enableDebug(bool enable) {
    debugEnabled = enable;
}

bool AsymmetricPIDModule::isDebugEnabled() {
    return debugEnabled;
}
// Basic control methods (add at end of file)
void AsymmetricPIDModule::start() {
    clearFailsafe();
    coolingPID.SetMode(AUTOMATIC);
    heatingPID.SetMode(AUTOMATIC);
    active = true;
    comm.sendEvent("🚀 Asymmetric PID started");
}

void AsymmetricPIDModule::stop() {
    coolingPID.SetMode(MANUAL);
    heatingPID.SetMode(MANUAL);
    active = false;
    finalOutput = 0;
    coolingOutput = 0;
    heatingOutput = 0;
    pwm.setDutyCycle(0);
    digitalWrite(8, LOW);
    digitalWrite(7, LOW);
    comm.sendEvent("⏹️ Asymmetric PID stopped");
}

bool AsymmetricPIDModule::isActive() {
    return active;
}