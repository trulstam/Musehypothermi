// ===================== sensor_module.cpp =====================
#include "sensor_module.h"

#include "arduino_platform.h"
#include <math.h>
#include "pid_module.h"
#include "eeprom_manager.h"
#include <string.h>

extern PIDModule pid;

#if SIMULATION_MODE
static double coolingPlateTemp = 22.0;
static double rectalTemp = 37.0;

const double plateThermalMass = 0.3;
const double plateSpecificHeat = 900.0;
const double plateCoolingLoss = 0.01;

const double rectalThermalMass = 0.03;
const double rectalSpecificHeat = 3470.0;
const double rectalCoupling = 0.02;
#endif

SensorModule::SensorModule()
  : calibrationOffsetCooling(0.0), calibrationOffsetRectal(0.0),
    cachedCoolingPlateTemp(0.0), cachedRectalTemp(0.0),
    lastRawCoolingPlateTemp(0.0), lastRawRectalTemp(0.0) {}

void SensorModule::begin() {
  analogReadResolution(14);
  analogReference(AR_EXTERNAL);  // Bruk AR_DEFAULT hvis ingen ekstern referanse

  calibrationOffsetCooling = 0.0;
  calibrationOffsetRectal = 0.0;
  cachedCoolingPlateTemp = 0.0;
  cachedRectalTemp = 0.0;
  lastRawCoolingPlateTemp = 0.0;
  lastRawRectalTemp = 0.0;

  plateCalCount = 0;
  rectalCalCount = 0;

  memset(&plateMeta, 0, sizeof(plateMeta));
  memset(&rectalMeta, 0, sizeof(rectalMeta));
}

void SensorModule::loadCalibration(const EEPROMManager &eeprom) {
  eeprom.loadPlateCalibration(plateCalTable, plateCalCount);
  eeprom.loadRectalCalibration(rectalCalTable, rectalCalCount);

  eeprom.getPlateCalibrationMeta(plateMeta);
  eeprom.getRectalCalibrationMeta(rectalMeta);

  // Ensure tables are sorted (EEPROM may contain unordered points from older commits)
  sortCalibrationTable(plateCalTable, plateCalCount);
  sortCalibrationTable(rectalCalTable, rectalCalCount);
}

void SensorModule::update() {
  updateTemps();
}

void SensorModule::updateTemps() {
#if SIMULATION_MODE
  static unsigned long lastUpdate = millis();
  unsigned long now = millis();
  double deltaTime = (now - lastUpdate) / 1000.0;
  if (deltaTime <= 0.0) return;
  lastUpdate = now;

  double pwmOutput = pid.getPwmOutput();
  double peltierPower = (pwmOutput / 2399.0) * 120.0;

  double ambientTemp = 22.0;
  double heatLoss = plateCoolingLoss * (coolingPlateTemp - ambientTemp);
  double deltaQPlate = (peltierPower - heatLoss) * deltaTime;
  double deltaTempPlate = deltaQPlate / (plateThermalMass * plateSpecificHeat);
  coolingPlateTemp += deltaTempPlate;

  double metabolicPower = map(rectalTemp, 14.0, 37.0, 0.01, 0.21);

  double deltaQRectal = rectalCoupling * (coolingPlateTemp - rectalTemp) * deltaTime
                      + metabolicPower * deltaTime;
  double deltaTempRectal = deltaQRectal / (rectalThermalMass * rectalSpecificHeat);
  rectalTemp += deltaTempRectal;

  coolingPlateTemp = constrain(coolingPlateTemp, -10.0, 50.0);
  rectalTemp = constrain(rectalTemp, 14.0, 40.0);

  int adcNoiseRaw = analogRead(A3);
  double noise = map(adcNoiseRaw, 0, 16383, -0.05, 0.05);

  double rawPlate = coolingPlateTemp + noise;
  double rawRectal = rectalTemp + noise;

  lastRawCoolingPlateTemp = rawPlate;   // Råverdi (simulert)
  lastRawRectalTemp = rawRectal;

  cachedCoolingPlateTemp = applyCalibration(rawPlate + calibrationOffsetCooling,
                                            plateCalTable, plateCalCount);
  cachedRectalTemp = applyCalibration(rawRectal + calibrationOffsetRectal,
                                      rectalCalTable, rectalCalCount);
#else
  int rawPlate = analogRead(COOLING_PLATE_PIN);
  int rawRectal = analogRead(RECTAL_PROBE_PIN);

  double rawPlateTemp  = convertRawToTemp(rawPlate);
  double rawRectalTemp = convertRawToTemp(rawRectal);

  lastRawCoolingPlateTemp = rawPlateTemp;   // Lagre råverdi (ADC → °C)
  lastRawRectalTemp       = rawRectalTemp;

  cachedCoolingPlateTemp = applyCalibration(rawPlateTemp + calibrationOffsetCooling,
                                            plateCalTable, plateCalCount);
  cachedRectalTemp       = applyCalibration(rawRectalTemp + calibrationOffsetRectal,
                                            rectalCalTable, rectalCalCount);
#endif
}

double SensorModule::getCoolingPlateTemp() {
  return cachedCoolingPlateTemp;
}

double SensorModule::getRectalTemp() {
  return cachedRectalTemp;
}

double SensorModule::getCoolingPlateRawTemp() const {
  return lastRawCoolingPlateTemp;
}

double SensorModule::getRectalRawTemp() const {
  return lastRawRectalTemp;
}

void SensorModule::setCoolingCalibration(double offset) {
  calibrationOffsetCooling = offset;
}

void SensorModule::setRectalCalibration(double offset) {
  calibrationOffsetRectal = offset;
}

void SensorModule::setSimulatedTemps(double plate, double rectal) {
  cachedCoolingPlateTemp = plate;
  cachedRectalTemp = rectal;
}

bool SensorModule::addCalibrationPoint(const char *sensorName, float reference) {
  CalibrationPoint *table = nullptr;
  uint8_t *count = nullptr;
  SensorCalibrationMeta *meta = nullptr;
  if (!selectCalibration(sensorName, table, count, meta)) {
    return false;
  }

  if (!table || !count || *count >= CALIB_MAX_POINTS) {
    return false;
  }

  double measured = 0.0;
  if (strcmp(sensorName, "rectal") == 0) {
    measured = lastRawRectalTemp;
  } else {
    measured = lastRawCoolingPlateTemp;
  }

  CalibrationPoint point{};
  point.measured = static_cast<float>(measured);
  point.reference = reference;

  table[*count] = point;
  (*count)++;
  sortCalibrationTable(table, *count);
  return true;
}

bool SensorModule::commitCalibration(const char *sensorName,
                                     const char *operatorName,
                                     uint32_t timestamp,
                                     EEPROMManager &eeprom) {
  CalibrationPoint *table = nullptr;
  uint8_t *count = nullptr;
  SensorCalibrationMeta *meta = nullptr;
  if (!selectCalibration(sensorName, table, count, meta)) {
    return false;
  }

  if (!table || !count || *count == 0) {
    return false;
  }

  if (strcmp(sensorName, "rectal") == 0) {
    if (!eeprom.saveRectalCalibration(table, *count, operatorName, timestamp)) return false;
  } else {
    if (!eeprom.savePlateCalibration(table, *count, operatorName, timestamp)) return false;
  }

  if (meta) {
    meta->timestamp = timestamp;
    meta->pointCount = *count;
    if (operatorName) {
      strncpy(meta->operatorName, operatorName, sizeof(meta->operatorName) - 1);
      meta->operatorName[sizeof(meta->operatorName) - 1] = '\0';
    }
  }

  return true;
}

bool SensorModule::getCalibrationTable(const char *sensorName,
                                       CalibrationPoint *outTable,
                                       uint8_t &count) const {
  const CalibrationPoint *table = nullptr;
  const uint8_t *tableCount = nullptr;
  const SensorCalibrationMeta *meta = nullptr;
  if (!selectCalibrationConst(sensorName, table, tableCount, meta)) {
    return false;
  }

  if (!table || !tableCount || *tableCount == 0 || !outTable) {
    count = 0;
    return false;
  }

  count = *tableCount;
  for (uint8_t i = 0; i < count; ++i) {
    outTable[i] = table[i];
  }
  return true;
}

void SensorModule::getCalibrationMeta(const char *sensorName, SensorCalibrationMeta &meta) const {
  const CalibrationPoint *table = nullptr;
  const uint8_t *tableCount = nullptr;
  const SensorCalibrationMeta *metaPtr = nullptr;
  if (!selectCalibrationConst(sensorName, table, tableCount, metaPtr) || !metaPtr) {
    memset(&meta, 0, sizeof(meta));
    return;
  }
  meta = *metaPtr;
}

double SensorModule::convertRawToTemp(int raw) {
  if (raw <= 0 || raw >= 16383) {
    Serial.println("{\"err\": \"Sensor raw value out of range\"}");
    return -273.15;  // Invalid temp marker
  }

  double voltage = (raw / 16383.0) * 4.096;  // 14-bit ADC scaling
  double resistance = (voltage / (4.096 - voltage)) * 10000.0;  // 10k pull-up
  double tempK = 1.0 / (1.0 / 298.15 + (1.0 / 3988.0) * log(resistance / 10000.0));
  return tempK - 273.15;  // Kelvin to Celsius
}

double SensorModule::applyCalibration(double raw, const CalibrationPoint *table, uint8_t count) const {
  if (count == 0 || !table) return raw;

  if (count == 1) {
    double delta = static_cast<double>(table[0].reference - table[0].measured);
    return raw + delta;
  }

  if (raw <= table[0].measured) {
    return table[0].reference;
  }

  if (raw >= table[count - 1].measured) {
    return table[count - 1].reference;
  }

  for (uint8_t i = 1; i < count; ++i) {
    double x0 = table[i - 1].measured;
    double x1 = table[i].measured;
    if (raw <= x1) {
      double y0 = table[i - 1].reference;
      double y1 = table[i].reference;
      double ratio = (raw - x0) / (x1 - x0);
      return y0 + ratio * (y1 - y0);
    }
  }

  return raw;  // Fallback (should not be reached)
}

bool SensorModule::selectCalibration(const char *sensorName,
                                     CalibrationPoint *&table,
                                     uint8_t *&count,
                                     SensorCalibrationMeta *&meta) {
  if (!sensorName) return false;

  if (strcmp(sensorName, "rectal") == 0) {
    table = rectalCalTable;
    count = &rectalCalCount;
    meta = &rectalMeta;
    return true;
  }

  if (strcmp(sensorName, "plate") == 0) {
    table = plateCalTable;
    count = &plateCalCount;
    meta = &plateMeta;
    return true;
  }

  return false;
}

bool SensorModule::selectCalibrationConst(const char *sensorName,
                                          const CalibrationPoint *&table,
                                          uint8_t const *&count,
                                          const SensorCalibrationMeta *&meta) const {
  if (!sensorName) return false;

  if (strcmp(sensorName, "rectal") == 0) {
    table = rectalCalTable;
    count = &rectalCalCount;
    meta = &rectalMeta;
    return true;
  }

  if (strcmp(sensorName, "plate") == 0) {
    table = plateCalTable;
    count = &plateCalCount;
    meta = &plateMeta;
    return true;
  }

  return false;
}

void SensorModule::sortCalibrationTable(CalibrationPoint *table, uint8_t count) {
  if (!table || count < 2) return;

  for (uint8_t i = 1; i < count; ++i) {
    CalibrationPoint key = table[i];
    int j = i - 1;
    while (j >= 0 && table[j].measured > key.measured) {
      table[j + 1] = table[j];
      if (j == 0) break;
      j--;
    }
    if (table[j].measured <= key.measured) {
      table[j + 1] = key;
    } else {
      table[0] = key;
    }
  }
}
