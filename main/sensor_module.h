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
    void updateCalibrationData(EEPROMManager::SensorType sensor, const float *raw,
                               const float *actual, int count);
    void printCalibration(EEPROMManager::SensorType sensor);

  private:
    struct CalibrationTable {
        float raw[5];
        float actual[5];
        int count = 0;
    };

    double convertRawToTemp(int raw);
    float applyCalibration(const CalibrationTable &table, float rawValue);

    CalibrationTable rectalTable;
    CalibrationTable plateTable;

    double cachedCoolingPlateTemp;
    double cachedRectalTemp;
    double cachedRawCoolingPlateTemp;
    double cachedRawRectalTemp;

    static const uint8_t COOLING_PLATE_PIN = A1;
    static const uint8_t RECTAL_PROBE_PIN = A2;
};

#endif // SENSOR_MODULE_H
