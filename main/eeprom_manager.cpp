#include "eeprom_manager.h"
#include <EEPROM.h>

// Initiering av static const
const uint32_t EEPROMManager::MAGIC_NUMBER = 0xDEADBEEF;

// Ingen EEPROM.begin() kreves for Uno R4 Minima

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
    saveHeatingPIDParams(2.0f, 0.5f, 1.0f);
    saveCoolingPIDParams(1.5f, 0.3f, 0.8f);
    saveTargetTemp(37.0f);
    saveMaxOutput(35.0f);
    saveCoolingRateLimit(2.0f);
    saveDeadband(0.5f);
    saveSafetyMargin(2.0f);
    saveDebugLevel(0);
    saveFailsafeTimeout(5000);

    saveMagicNumber();

    return true;
}

void EEPROMManager::saveMagicNumber() {
    EEPROM.put(addrMagic, MAGIC_NUMBER);
}

bool EEPROMManager::isMagicNumberValid() {
    uint32_t magic;
    EEPROM.get(addrMagic, magic);
    return (magic == MAGIC_NUMBER);
}
