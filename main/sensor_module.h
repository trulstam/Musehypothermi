// Musehypothermi Arduino Sensor Module - Class Version
// File: sensor_module.h

#ifndef SENSOR_MODULE_H
#define SENSOR_MODULE_H  // <-- DETTE ER VIKTIG!

#include "arduino_platform.h"  // <-- IKKE "sensor_module.h"!

class EEPROMManager;

class SensorModule {
  public:
    struct CalibrationPoint {
        float measured;   // Raw temperature from sensor conversion (°C)
        float reference;  // True/calibrated temperature (°C)
    };

    static const uint8_t MAX_CAL_POINTS = 8;

    SensorModule();

    void begin();
    void update();

    double getCoolingPlateTemp();
    double getRectalTemp();

    void setCoolingCalibration(double offset);
    void setRectalCalibration(double offset);
    void setSimulatedTemps(double plate, double rectal);

    // Calibration API (called from CommAPI)
    bool addCalibrationPoint(const char* sensorName, float referenceTemp);
    bool commitCalibration(const char* sensorName, const char* operatorName, uint32_t timestamp);

  private:
    CalibrationPoint plateCalTable[MAX_CAL_POINTS];
    uint8_t plateCalCount;

    CalibrationPoint rectalCalTable[MAX_CAL_POINTS];
    uint8_t rectalCalCount;

    double convertRawToTemp(int raw);
    double applyCalibration(double rawTemp,
                            const CalibrationPoint* table,
                            uint8_t count) const;

    class EEPROMManager* eepromManagerPointer;

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
