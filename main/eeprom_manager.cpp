#include "eeprom_manager.h"

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
    return false;
}

void EEPROMManager::savePIDParams(float kp, float ki, float kd) {
    saveHeatingPIDParams(kp, ki, kd);
}

void EEPROMManager::loadPIDParams(float &kp, float &ki, float &kd) {
    loadHeatingPIDParams(kp, ki, kd);
}

void EEPROMManager::saveHeatingPIDParams(float kp, float ki, float kd) {
    EEPROM.put(addrKp, kp);
    EEPROM.put(addrKi, ki);
    EEPROM.put(addrKd, kd);
}

void EEPROMManager::loadHeatingPIDParams(float &kp, float &ki, float &kd) {
    EEPROM.get(addrKp, kp);
    EEPROM.get(addrKi, ki);
    EEPROM.get(addrKd, kd);
}

void EEPROMManager::saveCoolingPIDParams(float kp, float ki, float kd) {
    EEPROM.put(addrCoolingKp, kp);
    EEPROM.put(addrCoolingKi, ki);
    EEPROM.put(addrCoolingKd, kd);
}

void EEPROMManager::loadCoolingPIDParams(float &kp, float &ki, float &kd) {
    EEPROM.get(addrCoolingKp, kp);
    EEPROM.get(addrCoolingKi, ki);
    EEPROM.get(addrCoolingKd, kd);
}

void EEPROMManager::saveTargetTemp(float temp) {
    EEPROM.put(addrTargetTemp, temp);
}

void EEPROMManager::loadTargetTemp(float &temp) {
    EEPROM.get(addrTargetTemp, temp);
}

void EEPROMManager::saveMaxOutput(float maxOutput) {
    saveHeatingMaxOutput(maxOutput);
    saveCoolingMaxOutput(maxOutput);
}

void EEPROMManager::loadMaxOutput(float &maxOutput) {
    loadHeatingMaxOutput(maxOutput);
}

void EEPROMManager::saveHeatingMaxOutput(float maxOutput) {
    EEPROM.put(addrHeatingMaxOutput, maxOutput);
}

void EEPROMManager::loadHeatingMaxOutput(float &maxOutput) {
    EEPROM.get(addrHeatingMaxOutput, maxOutput);
}

void EEPROMManager::saveCoolingMaxOutput(float maxOutput) {
    EEPROM.put(addrCoolingMaxOutput, maxOutput);
}

void EEPROMManager::loadCoolingMaxOutput(float &maxOutput) {
    EEPROM.get(addrCoolingMaxOutput, maxOutput);
}

void EEPROMManager::saveOutputLimits(const OutputLimits &limits) {
    saveHeatingMaxOutput(limits.heatingPercent);
    saveCoolingMaxOutput(limits.coolingPercent);
}

void EEPROMManager::loadOutputLimits(OutputLimits &limits) {
    loadHeatingMaxOutput(limits.heatingPercent);
    loadCoolingMaxOutput(limits.coolingPercent);
}

void EEPROMManager::saveCoolingRateLimit(float rate) {
    EEPROM.put(addrCoolingRateLimit, rate);
}

void EEPROMManager::loadCoolingRateLimit(float &rate) {
    EEPROM.get(addrCoolingRateLimit, rate);
}

void EEPROMManager::saveDeadband(float deadband) {
    EEPROM.put(addrDeadband, deadband);
}

void EEPROMManager::loadDeadband(float &deadband) {
    EEPROM.get(addrDeadband, deadband);
}

void EEPROMManager::saveSafetyMargin(float margin) {
    EEPROM.put(addrSafetyMargin, margin);
}

void EEPROMManager::loadSafetyMargin(float &margin) {
    EEPROM.get(addrSafetyMargin, margin);
}

void EEPROMManager::saveSafetySettings(const SafetySettings &settings) {
    saveCoolingRateLimit(settings.coolingRateLimit);
    saveDeadband(settings.deadband);
    saveSafetyMargin(settings.safetyMargin);
}

void EEPROMManager::loadSafetySettings(SafetySettings &settings) {
    loadCoolingRateLimit(settings.coolingRateLimit);
    loadDeadband(settings.deadband);
    loadSafetyMargin(settings.safetyMargin);
}

void EEPROMManager::saveDebugLevel(int debugLevel) {
    EEPROM.put(addrDebugLevel, debugLevel);
}

void EEPROMManager::loadDebugLevel(int &debugLevel) {
    EEPROM.get(addrDebugLevel, debugLevel);
}

void EEPROMManager::saveFailsafeTimeout(int timeout) {
    EEPROM.put(addrFailsafeTimeout, timeout);
}

void EEPROMManager::loadFailsafeTimeout(int &timeout) {
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
