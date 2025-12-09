// ===================== sensor_module.cpp =====================
#include "sensor_module.h"

#include "arduino_platform.h"
#include <math.h>
#include <string.h>
#include "pid_module_asymmetric.h"

extern AsymmetricPIDModule pid;

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
  : cachedCoolingPlateTemp(0.0), cachedRectalTemp(0.0),
    cachedRawCoolingPlateTemp(0.0), cachedRawRectalTemp(0.0) {}

void SensorModule::begin(EEPROMManager &eepromManager) {
  analogReadResolution(14);
  analogReference(AR_EXTERNAL);  // Bruk AR_DEFAULT hvis ingen ekstern referanse
  float raw[5] = {};
  float actual[5] = {};
  int count = 0;

  eepromManager.loadCalibrationPoints(EEPROMManager::SensorType::Plate, raw, actual,
                                      count);
  updateCalibrationData(EEPROMManager::SensorType::Plate, raw, actual, count);

  eepromManager.loadCalibrationPoints(EEPROMManager::SensorType::Rectal, raw, actual,
                                      count);
  updateCalibrationData(EEPROMManager::SensorType::Rectal, raw, actual, count);
}

void SensorModule::update() {
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

  cachedRawCoolingPlateTemp = coolingPlateTemp + noise;
  cachedRawRectalTemp = rectalTemp + noise;
#else
  int rawCooling = analogRead(COOLING_PLATE_PIN);
  int rawRectal = analogRead(RECTAL_PROBE_PIN);

  double rawCoolingTemp = convertRawToTemp(rawCooling);
  double rawRectalTemp = convertRawToTemp(rawRectal);

  cachedRawCoolingPlateTemp = rawCoolingTemp;
  cachedRawRectalTemp = rawRectalTemp;
#endif

  cachedCoolingPlateTemp = applyCalibration(plateTable, cachedRawCoolingPlateTemp);
  cachedRectalTemp = applyCalibration(rectalTable, cachedRawRectalTemp);
}

double SensorModule::getCoolingPlateTemp() {
  return cachedCoolingPlateTemp;
}

double SensorModule::getRectalTemp() {
  return cachedRectalTemp;
}

double SensorModule::getRawCoolingPlateTemp() {
  return cachedRawCoolingPlateTemp;
}

double SensorModule::getRawRectalTemp() {
  return cachedRawRectalTemp;
}

void SensorModule::setSimulatedTemps(double plate, double rectal) {
  cachedCoolingPlateTemp = plate;
  cachedRectalTemp = rectal;
  cachedRawCoolingPlateTemp = plate;
  cachedRawRectalTemp = rectal;
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

float SensorModule::applyCalibration(const CalibrationTable &table, float rawValue) {
  if (table.count == 0) {
    return rawValue;
  }

  if (table.count == 1) {
    float offset = table.actual[0] - table.raw[0];
    return rawValue + offset;
  }

  auto interpolate = [](float raw, float x1, float y1, float x2, float y2) {
    float denom = (x2 - x1);
    if (denom == 0.0f) {
      return y1;
    }
    float t = (raw - x1) / denom;
    return y1 + t * (y2 - y1);
  };

  if (rawValue <= table.raw[0]) {
    return interpolate(rawValue, table.raw[0], table.actual[0], table.raw[1],
                      table.actual[1]);
  }

  if (rawValue >= table.raw[table.count - 1]) {
    return interpolate(rawValue, table.raw[table.count - 2],
                      table.actual[table.count - 2], table.raw[table.count - 1],
                      table.actual[table.count - 1]);
  }

  for (int i = 0; i < table.count - 1; ++i) {
    if (rawValue >= table.raw[i] && rawValue <= table.raw[i + 1]) {
      return interpolate(rawValue, table.raw[i], table.actual[i], table.raw[i + 1],
                        table.actual[i + 1]);
    }
  }

  return rawValue;
}

void SensorModule::updateCalibrationData(EEPROMManager::SensorType sensor, const float *raw,
                                         const float *actual, int count) {
  CalibrationTable &table = (sensor == EEPROMManager::SensorType::Rectal) ? rectalTable
                                                                           : plateTable;

  if (count <= 0) {
    table.count = 0;
    return;
  }

  const int clampedCount = count > 5 ? 5 : count;

  struct Point {
    float rawValue;
    float actualValue;
  } points[5];

  for (int i = 0; i < clampedCount; ++i) {
    points[i].rawValue = raw[i];
    points[i].actualValue = actual[i];
  }

  for (int i = 1; i < clampedCount; ++i) {
    Point key = points[i];
    int j = i - 1;
    while (j >= 0 && points[j].rawValue > key.rawValue) {
      points[j + 1] = points[j];
      --j;
    }
    points[j + 1] = key;
  }

  for (int i = 0; i < clampedCount; ++i) {
    table.raw[i] = points[i].rawValue;
    table.actual[i] = points[i].actualValue;
  }
  table.count = clampedCount;
}

void SensorModule::printCalibration(EEPROMManager::SensorType sensor) {
  const CalibrationTable &table =
      (sensor == EEPROMManager::SensorType::Rectal) ? rectalTable : plateTable;
  Serial.print("Calibration (");
  Serial.print((sensor == EEPROMManager::SensorType::Rectal) ? "Rectal" : "Plate");
  Serial.println("):");
  for (int i = 0; i < table.count; ++i) {
    Serial.print("  Raw: ");
    Serial.print(table.raw[i]);
    Serial.print(" → Actual: ");
    Serial.println(table.actual[i]);
  }
}
