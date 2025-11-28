#include "eeprom_manager.h"

#include <string.h>

namespace {
constexpr float kDefaultHeatingKp = 2.0f;
constexpr float kDefaultHeatingKi = 0.5f;
constexpr float kDefaultHeatingKd = 1.0f;

constexpr float kDefaultCoolingKp = 1.5f;
constexpr float kDefaultCoolingKi = 0.3f;
constexpr float kDefaultCoolingKd = 0.8f;

constexpr float kDefaultTargetTemp = 37.0f;
constexpr float kDefaultMaxOutput = 35.0f;
constexpr float kDefaultCoolingRate = 2.0f;
constexpr float kDefaultDeadband = 0.5f;
constexpr float kDefaultSafetyMargin = 2.0f;
constexpr int kDefaultDebugLevel = 0;
constexpr int kDefaultFailsafeTimeout = 5000;
}

const uint32_t EEPROMManager::MAGIC_NUMBER = 0xDEADBEEF;

bool EEPROMManager::begin() {
    if (!isMagicNumberValid()) {
        return factoryReset();
    }
    return true;
}

void EEPROMManager::savePIDParams(float kp, float ki, float kd) {
    saveHeatingPIDParams(kp, ki, kd);
}

void EEPROMManager::loadPIDParams(float &kp, float &ki, float &kd) const {
    loadHeatingPIDParams(kp, ki, kd);
}

void EEPROMManager::saveHeatingPIDParams(float kp, float ki, float kd) {
    EEPROM.put(addrKp, kp);
    EEPROM.put(addrKi, ki);
    EEPROM.put(addrKd, kd);
}

void EEPROMManager::loadHeatingPIDParams(float &kp, float &ki, float &kd) const {
    EEPROM.get(addrKp, kp);
    EEPROM.get(addrKi, ki);
    EEPROM.get(addrKd, kd);
}

void EEPROMManager::saveCoolingPIDParams(float kp, float ki, float kd) {
    EEPROM.put(addrCoolingKp, kp);
    EEPROM.put(addrCoolingKi, ki);
    EEPROM.put(addrCoolingKd, kd);
}

void EEPROMManager::loadCoolingPIDParams(float &kp, float &ki, float &kd) const {
    EEPROM.get(addrCoolingKp, kp);
    EEPROM.get(addrCoolingKi, ki);
    EEPROM.get(addrCoolingKd, kd);
}

void EEPROMManager::saveTargetTemp(float temp) {
    EEPROM.put(addrTargetTemp, temp);
}

void EEPROMManager::loadTargetTemp(float &temp) const {
    EEPROM.get(addrTargetTemp, temp);
}

void EEPROMManager::saveMaxOutput(float maxOutput) {
    saveHeatingMaxOutput(maxOutput);
    saveCoolingMaxOutput(maxOutput);
}

void EEPROMManager::loadMaxOutput(float &maxOutput) const {
    loadHeatingMaxOutput(maxOutput);
}

void EEPROMManager::saveHeatingMaxOutput(float maxOutput) {
    EEPROM.put(addrHeatingMaxOutput, maxOutput);
}

void EEPROMManager::loadHeatingMaxOutput(float &maxOutput) const {
    EEPROM.get(addrHeatingMaxOutput, maxOutput);
}

void EEPROMManager::saveCoolingMaxOutput(float maxOutput) {
    EEPROM.put(addrCoolingMaxOutput, maxOutput);
}

void EEPROMManager::loadCoolingMaxOutput(float &maxOutput) const {
    EEPROM.get(addrCoolingMaxOutput, maxOutput);
}

void EEPROMManager::saveOutputLimits(const OutputLimits &limits) {
    saveHeatingMaxOutput(limits.heatingPercent);
    saveCoolingMaxOutput(limits.coolingPercent);
}

void EEPROMManager::loadOutputLimits(OutputLimits &limits) const {
    loadHeatingMaxOutput(limits.heatingPercent);
    loadCoolingMaxOutput(limits.coolingPercent);
}

void EEPROMManager::saveSafetySettings(const SafetySettings &settings) {
    EEPROM.put(addrCoolingRateLimit, settings.coolingRateLimit);
    EEPROM.put(addrDeadband, settings.deadband);
    EEPROM.put(addrSafetyMargin, settings.safetyMargin);
}

void EEPROMManager::loadSafetySettings(SafetySettings &settings) const {
    EEPROM.get(addrCoolingRateLimit, settings.coolingRateLimit);
    EEPROM.get(addrDeadband, settings.deadband);
    EEPROM.get(addrSafetyMargin, settings.safetyMargin);
}

namespace {
void sortCalibrationPoints(EEPROMManager::CalibrationData &data) {
    if (data.pointCount <= 1 || data.pointCount > 5) {
        return;
    }

    for (uint8_t i = 1; i < data.pointCount; ++i) {
        EEPROMManager::CalibrationPoint key = data.points[i];
        int j = i - 1;
        while (j >= 0 && data.points[j].rawValue > key.rawValue) {
            data.points[j + 1] = data.points[j];
            --j;
        }
        data.points[j + 1] = key;
    }
}
}

void EEPROMManager::saveCalibrationData(uint8_t sensorId, const CalibrationData &data) {
    CalibrationData sorted = data;
    if (sorted.pointCount > 5) {
        sorted.pointCount = 5;
    }
    sortCalibrationPoints(sorted);
    int addr = (sensorId == CALIB_SENSOR_PLATE) ? addrPlateCalibration : addrRectalCalibration;
    EEPROM.put(addr, sorted);
}

void EEPROMManager::loadCalibrationData(uint8_t sensorId, CalibrationData &data) const {
    CalibrationData tmp{};
    int addr = (sensorId == CALIB_SENSOR_PLATE) ? addrPlateCalibration : addrRectalCalibration;
    EEPROM.get(addr, tmp);

    // Basic validation: limit pointCount and ensure null-termination
    if (tmp.pointCount > 5) {
        tmp.pointCount = 0;
    }
    tmp.lastCalUser[15] = '\0';
    tmp.lastCalTimestamp[19] = '\0';
    sortCalibrationPoints(tmp);
    data = tmp;
}

void EEPROMManager::factoryResetCalibration() {
    CalibrationData empty{};
    empty.pointCount = 0;
    empty.lastCalUser[0] = '\0';
    empty.lastCalTimestamp[0] = '\0';
    for (uint8_t i = 0; i < 5; ++i) {
        empty.points[i].rawValue = 0.0f;
        empty.points[i].refValue = 0.0f;
    }
    saveCalibrationData(CALIB_SENSOR_RECTAL, empty);
    saveCalibrationData(CALIB_SENSOR_PLATE, empty);
}

void EEPROMManager::saveDebugLevel(int debugLevel) {
    EEPROM.put(addrDebugLevel, debugLevel);
}

void EEPROMManager::loadDebugLevel(int &debugLevel) const {
    EEPROM.get(addrDebugLevel, debugLevel);
}

void EEPROMManager::saveFailsafeTimeout(int timeout) {
    EEPROM.put(addrFailsafeTimeout, timeout);
}

void EEPROMManager::loadFailsafeTimeout(int &timeout) const {
    EEPROM.get(addrFailsafeTimeout, timeout);
}

bool EEPROMManager::factoryReset() {
    saveHeatingPIDParams(kDefaultHeatingKp, kDefaultHeatingKi, kDefaultHeatingKd);
    saveCoolingPIDParams(kDefaultCoolingKp, kDefaultCoolingKi, kDefaultCoolingKd);
    saveTargetTemp(kDefaultTargetTemp);
    saveMaxOutput(kDefaultMaxOutput);

    SafetySettings safety{
        kDefaultCoolingRate,
        kDefaultDeadband,
        kDefaultSafetyMargin,
    };
    saveSafetySettings(safety);

    saveDebugLevel(kDefaultDebugLevel);
    saveFailsafeTimeout(kDefaultFailsafeTimeout);
    factoryResetCalibration();

    saveMagicNumber();
    return true;
}

void EEPROMManager::saveMagicNumber() {
    EEPROM.put(addrMagic, MAGIC_NUMBER);
}

bool EEPROMManager::isMagicNumberValid() const {
    uint32_t magic = 0;
    EEPROM.get(addrMagic, magic);
    return magic == MAGIC_NUMBER;
}
