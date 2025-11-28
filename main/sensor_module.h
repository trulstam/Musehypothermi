// Musehypothermi Arduino Sensor Module - Class Version
// File: sensor_module.h

#ifndef SENSOR_MODULE_H
#define SENSOR_MODULE_H  // <-- DETTE ER VIKTIG!

#include "arduino_platform.h"  // <-- IKKE "sensor_module.h"!
#include "eeprom_manager.h"

class SensorModule {
  public:
    SensorModule();

    void begin(EEPROMManager &eepromManager);
    void update();

    double getCoolingPlateTemp();
    double getRectalTemp();
    double getRawCoolingPlateTemp();
    double getRawRectalTemp();

    void setSimulatedTemps(double plate, double rectal);
    void updateCalibrationData(uint8_t sensorId, const EEPROMManager::CalibrationData &data);

  private:
    double convertRawToTemp(int raw);
    float applyCalibration(float rawTemp, const EEPROMManager::CalibrationData &data);

    EEPROMManager::CalibrationData rectalCalibration;
    EEPROMManager::CalibrationData plateCalibration;

    double cachedCoolingPlateTemp;
    double cachedRectalTemp;
    double cachedRawCoolingPlateTemp;
    double cachedRawRectalTemp;

    static const uint8_t COOLING_PLATE_PIN = A1;
    static const uint8_t RECTAL_PROBE_PIN = A2;
};

#endif // SENSOR_MODULE_H
