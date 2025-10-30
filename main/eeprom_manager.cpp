#include "eeprom_manager.h"

namespace {
constexpr float kDefaultHeatingKp = 2.0f;
constexpr float kDefaultHeatingKi = 0.5f;
constexpr float kDefaultHeatingKd = 1.0f;

constexpr float kDefaultCoolingKp = 1.5f;
constexpr float kDefaultCoolingKi = 0.3f;
constexpr float kDefaultCoolingKd = 0.8f;

constexpr float kDefaultTargetTemp = 37.0f;
constexpr float kDefaultMaxOutput = 20.0f;
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
