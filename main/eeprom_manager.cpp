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
    EEPROM.put(addrKp, kp);
    EEPROM.put(addrKi, ki);
    EEPROM.put(addrKd, kd);
}

void EEPROMManager::loadPIDParams(float &kp, float &ki, float &kd) {
    EEPROM.get(addrKp, kp);
    EEPROM.get(addrKi, ki);
    EEPROM.get(addrKd, kd);
}

void EEPROMManager::saveTargetTemp(float temp) {
    EEPROM.put(addrTargetTemp, temp);
}

void EEPROMManager::loadTargetTemp(float &temp) {
    EEPROM.get(addrTargetTemp, temp);
}

void EEPROMManager::saveMaxOutput(float maxOutput) {
    EEPROM.put(addrMaxOutput, maxOutput);
}

void EEPROMManager::loadMaxOutput(float &maxOutput) {
    EEPROM.get(addrMaxOutput, maxOutput);
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
    savePIDParams(2.0f, 0.5f, 1.0f);
    saveTargetTemp(37.0f);
    saveMaxOutput(35.0f);
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
