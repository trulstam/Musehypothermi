// Musehypothermi Arduino Sensor Module - Simplified (no table calibration)
// File: sensor_module.h

#ifndef SENSOR_MODULE_H
#define SENSOR_MODULE_H  // <-- DETTE ER VIKTIG!

#include "arduino_platform.h"  // <-- IKKE "sensor_module.h"!

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

  private:
    double convertRawToTemp(int raw);
    void updateTemps();

    double calibrationOffsetCooling;
    double calibrationOffsetRectal;

    double cachedCoolingPlateTemp;
    double cachedRectalTemp;

    double lastRawCoolingPlateTemp;
    double lastRawRectalTemp;

    static const uint8_t COOLING_PLATE_PIN = A1;
    static const uint8_t RECTAL_PROBE_PIN = A2;
};

#endif // SENSOR_MODULE_H
