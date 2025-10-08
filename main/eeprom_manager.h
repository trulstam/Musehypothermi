#ifndef EEPROM_MANAGER_H
#define EEPROM_MANAGER_H

#include <Arduino.h>
#include <EEPROM.h>

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

    bool begin();

    void savePIDParams(float kp, float ki, float kd);
    void loadPIDParams(float &kp, float &ki, float &kd);

    void saveHeatingPIDParams(float kp, float ki, float kd);
    void loadHeatingPIDParams(float &kp, float &ki, float &kd);

    void saveCoolingPIDParams(float kp, float ki, float kd);
    void loadCoolingPIDParams(float &kp, float &ki, float &kd);

    void saveTargetTemp(float temp);
    void loadTargetTemp(float &temp);

    void saveMaxOutput(float maxOutput);
    void loadMaxOutput(float &maxOutput);

    void saveHeatingMaxOutput(float maxOutput);
    void loadHeatingMaxOutput(float &maxOutput);

    void saveCoolingMaxOutput(float maxOutput);
    void loadCoolingMaxOutput(float &maxOutput);

    void saveOutputLimits(const OutputLimits &limits);
    void loadOutputLimits(OutputLimits &limits);

    void saveCoolingRateLimit(float rate);
    void loadCoolingRateLimit(float &rate);

    void saveDeadband(float deadband);
    void loadDeadband(float &deadband);

    void saveSafetyMargin(float margin);
    void loadSafetyMargin(float &margin);

    void saveSafetySettings(const SafetySettings &settings);
    void loadSafetySettings(SafetySettings &settings);

    void saveDebugLevel(int debugLevel);
    void loadDebugLevel(int &debugLevel);

    void saveFailsafeTimeout(int timeout);
    void loadFailsafeTimeout(int &timeout);

    bool factoryReset();

private:
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

    static const uint32_t MAGIC_NUMBER;

    void saveMagicNumber();
    bool isMagicNumberValid() const;
};

#endif  // EEPROM_MANAGER_H
