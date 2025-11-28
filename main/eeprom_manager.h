#ifndef EEPROM_MANAGER_H
#define EEPROM_MANAGER_H

#include "arduino_platform.h"
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

    struct CalibrationPoint {
        float rawValue;
        float refValue;
    };

    struct CalibrationData {
        uint8_t pointCount;
        CalibrationPoint points[5];
        char lastCalUser[16];
        char lastCalTimestamp[20];
    };

    enum CalibrationSensorId : uint8_t {
        CALIB_SENSOR_RECTAL = 0,
        CALIB_SENSOR_PLATE = 1,
    };

    bool begin();

    // Legacy single PID helpers (mirror original API)
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

    // Calibration data
    void saveCalibrationData(uint8_t sensorId, const CalibrationData &data);
    void loadCalibrationData(uint8_t sensorId, CalibrationData &data) const;
    void factoryResetCalibration();

    // Inline convenience wrappers operating on the composite safety blob
    inline void saveCoolingRateLimit(float rate);
    inline void loadCoolingRateLimit(float &rate);
    inline void saveDeadband(float deadband);
    inline void loadDeadband(float &deadband);
    inline void saveSafetyMargin(float margin);
    inline void loadSafetyMargin(float &margin);

    // Miscellaneous
    void saveDebugLevel(int debugLevel);
    void loadDebugLevel(int &debugLevel) const;
    void saveFailsafeTimeout(int timeout);
    void loadFailsafeTimeout(int &timeout) const;

    bool factoryReset();

private:
    // Flat address layout (no Layout struct / namespace)
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
    static const int addrRectalCalibration = addrSafetyMargin + sizeof(float);
    static const int addrPlateCalibration = addrRectalCalibration + sizeof(CalibrationData);

    static const uint32_t MAGIC_NUMBER;

    void saveMagicNumber();
    bool isMagicNumberValid() const;
};

// ---- Inline wrappers (use the composite SafetySettings block) ----
inline void EEPROMManager::saveCoolingRateLimit(float rate) {
    SafetySettings s{};
    loadSafetySettings(s);
    s.coolingRateLimit = rate;
    saveSafetySettings(s);
}

inline void EEPROMManager::loadCoolingRateLimit(float &rate) {
    SafetySettings s{};
    loadSafetySettings(s);
    rate = s.coolingRateLimit;
}

inline void EEPROMManager::saveDeadband(float deadband) {
    SafetySettings s{};
    loadSafetySettings(s);
    s.deadband = deadband;
    saveSafetySettings(s);
}

inline void EEPROMManager::loadDeadband(float &deadband) {
    SafetySettings s{};
    loadSafetySettings(s);
    deadband = s.deadband;
}

inline void EEPROMManager::saveSafetyMargin(float margin) {
    SafetySettings s{};
    loadSafetySettings(s);
    s.safetyMargin = margin;
    saveSafetySettings(s);
}

inline void EEPROMManager::loadSafetyMargin(float &margin) {
    SafetySettings s{};
    loadSafetySettings(s);
    margin = s.safetyMargin;
}

#endif // EEPROM_MANAGER_H
