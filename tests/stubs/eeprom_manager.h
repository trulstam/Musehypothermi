#pragma once

class EEPROMManager {
public:
    struct OutputLimits {
        float heatingPercent;
        float coolingPercent;
    };

    struct SafetySettings {
        float coolingRateLimit;
        float deadband;
        float safetyMargin;
    };

    void savePIDParams(float kp, float ki, float kd) {
        heatingKp = kp;
        heatingKi = ki;
        heatingKd = kd;
    }

    void loadPIDParams(float& kp, float& ki, float& kd) const {
        kp = heatingKp;
        ki = heatingKi;
        kd = heatingKd;
    }

    void saveHeatingPIDParams(float kp, float ki, float kd) {
        savePIDParams(kp, ki, kd);
    }

    void loadHeatingPIDParams(float& kp, float& ki, float& kd) const {
        loadPIDParams(kp, ki, kd);
    }

    void saveCoolingPIDParams(float kp, float ki, float kd) {
        coolingKp = kp;
        coolingKi = ki;
        coolingKd = kd;
    }

    void loadCoolingPIDParams(float& kp, float& ki, float& kd) const {
        kp = coolingKp;
        ki = coolingKi;
        kd = coolingKd;
    }

    void saveTargetTemp(float temp) { targetTemp = temp; }
    void loadTargetTemp(float& temp) const { temp = targetTemp; }

    void saveMaxOutput(float maxOutput) {
        heatingMaxOutput = maxOutput;
        coolingMaxOutput = maxOutput;
    }

    void loadMaxOutput(float& maxOutput) const { maxOutput = heatingMaxOutput; }

    void saveHeatingMaxOutput(float maxOutput) { heatingMaxOutput = maxOutput; }
    void loadHeatingMaxOutput(float& maxOutput) const { maxOutput = heatingMaxOutput; }

    void saveCoolingMaxOutput(float maxOutput) { coolingMaxOutput = maxOutput; }
    void loadCoolingMaxOutput(float& maxOutput) const { maxOutput = coolingMaxOutput; }

    void saveCoolingRateLimit(float rate) { coolingRateLimit = rate; }
    void loadCoolingRateLimit(float& rate) const { rate = coolingRateLimit; }

    void saveDeadband(float value) { deadband = value; }
    void loadDeadband(float& value) const { value = deadband; }

    void saveSafetyMargin(float value) { safetyMargin = value; }
    void loadSafetyMargin(float& value) const { value = safetyMargin; }

    void saveSafetySettings(const SafetySettings& settings) {
        coolingRateLimit = settings.coolingRateLimit;
        deadband = settings.deadband;
        safetyMargin = settings.safetyMargin;
    }

    void saveOutputLimits(const OutputLimits& limits) {
        heatingMaxOutput = limits.heatingPercent;
        coolingMaxOutput = limits.coolingPercent;
    }

    void saveDebugLevel(int) {}
    void saveFailsafeTimeout(int) {}

    void setInitialMaxOutput(float value) {
        heatingMaxOutput = value;
        coolingMaxOutput = value;
    }

private:
    float heatingKp = 2.0f;
    float heatingKi = 0.5f;
    float heatingKd = 1.0f;
    float coolingKp = 1.5f;
    float coolingKi = 0.3f;
    float coolingKd = 0.8f;
    float targetTemp = 37.0f;
    float heatingMaxOutput = 20.0f;
    float coolingMaxOutput = 20.0f;
    float coolingRateLimit = 2.0f;
    float deadband = 0.5f;
    float safetyMargin = 2.0f;
};

