#ifndef EEPROM_MANAGER_H
#define EEPROM_MANAGER_H

#include <Arduino.h>
#include <EEPROM.h>

class EEPROMManager {
public:
    bool begin();

    void savePIDParams(float kp, float ki, float kd);
    void loadPIDParams(float &kp, float &ki, float &kd);

    void saveTargetTemp(float temp);
    void loadTargetTemp(float &temp);

    void saveMaxOutput(float maxOutput);
    void loadMaxOutput(float &maxOutput);

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
    static const int addrMaxOutput = addrTargetTemp + sizeof(float);
    static const int addrDebugLevel = addrMaxOutput + sizeof(float);
    static const int addrFailsafeTimeout = addrDebugLevel + sizeof(int);
    static const int addrMagic = addrFailsafeTimeout + sizeof(int);

    // Bare deklarasjon, ikke initialisering her!
    static const uint32_t MAGIC_NUMBER;

    void saveMagicNumber();
    bool isMagicNumberValid();
};

#endif // EEPROM_MANAGER_H
