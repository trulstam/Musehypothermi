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
}  // namespace

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

bool EEPROMManager::savePlateCalibration(const SensorModule::CalibrationPoint* table,
                                          uint8_t count,
                                          const char* operatorName,
                                          uint32_t timestamp) {
    if (!table) {
        return false;
    }

    uint8_t clampedCount = count > SensorModule::MAX_CAL_POINTS ? SensorModule::MAX_CAL_POINTS : count;

    SensorCalibrationMeta meta{};
    meta.timestamp = timestamp;
    meta.pointCount = clampedCount;
    if (operatorName) {
        strncpy(meta.operatorName, operatorName, sizeof(meta.operatorName) - 1);
        meta.operatorName[sizeof(meta.operatorName) - 1] = '\0';
    } else {
        meta.operatorName[0] = '\0';
    }

    EEPROM.put(addrCalibPlateMeta, meta);

    for (uint8_t i = 0; i < clampedCount; ++i) {
        int addr = addrCalibPlateTable + i * sizeof(SensorModule::CalibrationPoint);
        EEPROM.put(addr, table[i]);
    }

    return true;
}

bool EEPROMManager::saveRectalCalibration(const SensorModule::CalibrationPoint* table,
                                           uint8_t count,
                                           const char* operatorName,
                                           uint32_t timestamp) {
    if (!table) {
        return false;
    }

    uint8_t clampedCount = count > SensorModule::MAX_CAL_POINTS ? SensorModule::MAX_CAL_POINTS : count;

    SensorCalibrationMeta meta{};
    meta.timestamp = timestamp;
    meta.pointCount = clampedCount;
    if (operatorName) {
        strncpy(meta.operatorName, operatorName, sizeof(meta.operatorName) - 1);
        meta.operatorName[sizeof(meta.operatorName) - 1] = '\0';
    } else {
        meta.operatorName[0] = '\0';
    }

    EEPROM.put(addrCalibRectalMeta, meta);

    for (uint8_t i = 0; i < clampedCount; ++i) {
        int addr = addrCalibRectalTable + i * sizeof(SensorModule::CalibrationPoint);
        EEPROM.put(addr, table[i]);
    }

    return true;
}

void EEPROMManager::loadPlateCalibration(SensorModule::CalibrationPoint* table,
                                         uint8_t& count) {
    if (!table) {
        count = 0;
        return;
    }

    SensorCalibrationMeta meta{};
    EEPROM.get(addrCalibPlateMeta, meta);

    if (meta.pointCount == 0 || meta.pointCount > SensorModule::MAX_CAL_POINTS || meta.timestamp == 0) {
        count = 0;
        return;
    }

    count = meta.pointCount;
    for (uint8_t i = 0; i < count; ++i) {
        int addr = addrCalibPlateTable + i * sizeof(SensorModule::CalibrationPoint);
        EEPROM.get(addr, table[i]);
    }
}

void EEPROMManager::loadRectalCalibration(SensorModule::CalibrationPoint* table,
                                          uint8_t& count) {
    if (!table) {
        count = 0;
        return;
    }

    SensorCalibrationMeta meta{};
    EEPROM.get(addrCalibRectalMeta, meta);

    if (meta.pointCount == 0 || meta.pointCount > SensorModule::MAX_CAL_POINTS || meta.timestamp == 0) {
        count = 0;
        return;
    }

    count = meta.pointCount;
    for (uint8_t i = 0; i < count; ++i) {
        int addr = addrCalibRectalTable + i * sizeof(SensorModule::CalibrationPoint);
        EEPROM.get(addr, table[i]);
    }
}

void EEPROMManager::getPlateCalibrationMeta(SensorCalibrationMeta& meta) const {
    EEPROM.get(addrCalibPlateMeta, meta);
}

void EEPROMManager::getRectalCalibrationMeta(SensorCalibrationMeta& meta) const {
    EEPROM.get(addrCalibRectalMeta, meta);
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

    SensorCalibrationMeta emptyMeta{};
    EEPROM.put(addrCalibPlateMeta, emptyMeta);
    EEPROM.put(addrCalibRectalMeta, emptyMeta);

    SensorModule::CalibrationPoint emptyPoint{};
    for (uint8_t i = 0; i < SensorModule::MAX_CAL_POINTS; ++i) {
        int plateAddr = addrCalibPlateTable + i * sizeof(SensorModule::CalibrationPoint);
        int rectalAddr = addrCalibRectalTable + i * sizeof(SensorModule::CalibrationPoint);
        EEPROM.put(plateAddr, emptyPoint);
        EEPROM.put(rectalAddr, emptyPoint);
    }

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
