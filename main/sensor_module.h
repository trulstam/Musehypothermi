// Musehypothermi Arduino Sensor Module - Class Version
// File: sensor_module.h

#ifndef SENSOR_MODULE_H
#define SENSOR_MODULE_H  // <-- DETTE ER VIKTIG!

#include "arduino_platform.h"  // <-- IKKE "sensor_module.h"!
#include "eeprom_manager.h"

class SensorModule {
  public:
    SensorModule();

    void begin();
    void update();

    double getCoolingPlateTemp();
    double getRectalTemp();

    double getCoolingPlateRawTemp() const;
    double getRectalRawTemp() const;

    void setCoolingCalibration(double offset);
    void setRectalCalibration(double offset);
    void setSimulatedTemps(double plate, double rectal);

    // Kalibrerings-API (kalles fra CommAPI)
    bool addCalibrationPoint(const char* sensorName, float referenceTemp);
    bool commitCalibration(const char* sensorName, const char* operatorName, uint32_t timestamp);

  private:
    double convertRawToTemp(int raw);
    void updateTemps();

    double calibrationOffsetCooling;
    double calibrationOffsetRectal;

    double cachedCoolingPlateTemp;
    double cachedRectalTemp;

    double lastRawCoolingPlateTemp;
    double lastRawRectalTemp;

    CalibrationPoint plateCalTable[CALIB_MAX_POINTS];
    uint8_t plateCalCount;

    CalibrationPoint rectalCalTable[CALIB_MAX_POINTS];
    uint8_t rectalCalCount;

    double applyCalibration(double rawTemp,
                            CalibrationPoint* table,
                            uint8_t count) const;  // Kalibrerer målt verdi mot referanse

    static const uint8_t COOLING_PLATE_PIN = A1;
    static const uint8_t RECTAL_PROBE_PIN = A2;
};

#endif // SENSOR_MODULE_H
