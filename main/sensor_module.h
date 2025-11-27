// Musehypothermi Arduino Sensor Module - With calibration tables
// File: sensor_module.h

#ifndef SENSOR_MODULE_H
#define SENSOR_MODULE_H  // <-- DETTE ER VIKTIG!

#include "arduino_platform.h"  // <-- IKKE "sensor_module.h"!
#include "eeprom_manager.h"

class SensorModule {
  public:
    SensorModule();

    void begin();
    void loadCalibration(const EEPROMManager &eeprom);
    void update();

    double getCoolingPlateTemp();
    double getRectalTemp();

    double getCoolingPlateRawTemp() const;
    double getRectalRawTemp() const;

    bool addCalibrationPoint(const char *sensorName, float reference);
    bool commitCalibration(const char *sensorName,
                           const char *operatorName,
                           uint32_t timestamp,
                           EEPROMManager &eeprom);

    bool getCalibrationTable(const char *sensorName,
                             CalibrationPoint *outTable,
                             uint8_t &count) const;

    void getCalibrationMeta(const char *sensorName, SensorCalibrationMeta &meta) const;

    void setCoolingCalibration(double offset);
    void setRectalCalibration(double offset);
    void setSimulatedTemps(double plate, double rectal);

  private:
    double convertRawToTemp(int raw);
    void updateTemps();
    double applyCalibration(double raw, const CalibrationPoint *table, uint8_t count) const;
    bool selectCalibration(const char *sensorName,
                           CalibrationPoint *&table,
                           uint8_t *&count,
                           SensorCalibrationMeta *&meta);
    bool selectCalibrationConst(const char *sensorName,
                                const CalibrationPoint *&table,
                                uint8_t const *&count,
                                const SensorCalibrationMeta *&meta) const;
    void sortCalibrationTable(CalibrationPoint *table, uint8_t count);

    double calibrationOffsetCooling;
    double calibrationOffsetRectal;

    CalibrationPoint plateCalTable[CALIB_MAX_POINTS];
    CalibrationPoint rectalCalTable[CALIB_MAX_POINTS];
    uint8_t plateCalCount{0};
    uint8_t rectalCalCount{0};
    SensorCalibrationMeta plateMeta{};
    SensorCalibrationMeta rectalMeta{};

    double cachedCoolingPlateTemp;
    double cachedRectalTemp;

    double lastRawCoolingPlateTemp;
    double lastRawRectalTemp;

    static const uint8_t COOLING_PLATE_PIN = A1;
    static const uint8_t RECTAL_PROBE_PIN = A2;
};

#endif // SENSOR_MODULE_H
