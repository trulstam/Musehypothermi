#ifndef EEPROM_MANAGER_H
#define EEPROM_MANAGER_H

#include <Arduino.h>
#include <EEPROM.h>

class EEPROMManager {
public:
    struct PIDParams {
        float kp;
        float ki;
        float kd;
    };

    struct OutputLimits {
        float heatingPercent;
        float coolingPercent;
    };

    struct SafetySettings {
        float coolingRateLimit;
        float deadband;
        float safetyMargin;
    };

    bool begin();

    // Legacy single PID helpers (mirror the original firmware API)
    void savePIDParams(float kp, float ki, float kd);
    void loadPIDParams(float &kp, float &ki, float &kd) const;

    // Dedicated asymmetric PID storage
    void saveHeatingPIDParams(float kp, float ki, float kd);
    void loadHeatingPIDParams(float &kp, float &ki, float &kd) const;
    void saveCoolingPIDParams(float kp, float ki, float kd);
    void loadCoolingPIDParams(float &kp, float &ki, float &kd) const;

    // Temperature target
    void saveTargetTemp(float temp);
    void loadTargetTemp(float &temp) const;

    // Output limits
    void saveMaxOutput(float maxOutput);
    void loadMaxOutput(float &maxOutput) const;
    void saveHeatingMaxOutput(float maxOutput);
    void loadHeatingMaxOutput(float &maxOutput) const;
    void saveCoolingMaxOutput(float maxOutput);
    void loadCoolingMaxOutput(float &maxOutput) const;
    void saveOutputLimits(const OutputLimits &limits);
    void loadOutputLimits(OutputLimits &limits) const;

    // Safety configuration (asymmetric controller)
    void saveSafetySettings(const SafetySettings &settings);
    void loadSafetySettings(SafetySettings &settings) const;

    // Inline convenience wrappers that operate on the composite safety blob.
    void saveCoolingRateLimit(float rate);
    void loadCoolingRateLimit(float &rate) const;
    void saveDeadband(float deadband);
    void loadDeadband(float &deadband) const;
    void saveSafetyMargin(float margin);
    void loadSafetyMargin(float &margin) const;

    // Miscellaneous
    void saveDebugLevel(int debugLevel);
    void loadDebugLevel(int &debugLevel) const;
    void saveFailsafeTimeout(int timeout);
    void loadFailsafeTimeout(int &timeout) const;

    bool factoryReset();

private:
    struct Layout {
        static const int addrKp = 0;
        static const int addrKi = addrKp + sizeof(float);
        static const int addrKd = addrKi + sizeof(float);
        static const int addrTargetTemp = addrKd + sizeof(float);
        static const int addrHeatingMaxOutput = addrTargetTemp + sizeof(float);
        static const int addrCoolingMaxOutput = addrHeatingMaxOutput + sizeof(float);
        static const int addrDebugLevel = addrCoolingMaxOutput + sizeof(float);
        static const int addrFailsafeTimeout = addrDebugLevel + sizeof(int);
        static const int addrMagic = addrFailsafeTimeout + sizeof(int);
        static const int addrCoolingKp = addrMagic + sizeof(uint32_t);
        static const int addrCoolingKi = addrCoolingKp + sizeof(float);
        static const int addrCoolingKd = addrCoolingKi + sizeof(float);
        static const int addrCoolingRateLimit = addrCoolingKd + sizeof(float);
        static const int addrDeadband = addrCoolingRateLimit + sizeof(float);
        static const int addrSafetyMargin = addrDeadband + sizeof(float);
    };

    static const uint32_t MAGIC_NUMBER;

    void saveMagicNumber();
    bool isMagicNumberValid() const;
};

inline void EEPROMManager::saveCoolingRateLimit(float rate) {
    SafetySettings settings{};
    loadSafetySettings(settings);
    settings.coolingRateLimit = rate;
    saveSafetySettings(settings);
}

inline void EEPROMManager::loadCoolingRateLimit(float &rate) const {
    SafetySettings settings{};
    loadSafetySettings(settings);
    rate = settings.coolingRateLimit;
}

inline void EEPROMManager::saveDeadband(float deadband) {
    SafetySettings settings{};
    loadSafetySettings(settings);
    settings.deadband = deadband;
    saveSafetySettings(settings);
}

inline void EEPROMManager::loadDeadband(float &deadband) const {
    SafetySettings settings{};
    loadSafetySettings(settings);
    deadband = settings.deadband;
}

inline void EEPROMManager::saveSafetyMargin(float margin) {
    SafetySettings settings{};
    loadSafetySettings(settings);
    settings.safetyMargin = margin;
    saveSafetySettings(settings);
}

inline void EEPROMManager::loadSafetyMargin(float &margin) const {
    SafetySettings settings{};
    loadSafetySettings(settings);
    margin = settings.safetyMargin;
}

#endif  // EEPROM_MANAGER_H
