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
  : rectalCalibration{}, plateCalibration{}, calibrationOffsetCooling(0.0),
    calibrationOffsetRectal(0.0), cachedCoolingPlateTemp(0.0),
    cachedRectalTemp(0.0), cachedRawCoolingPlateTemp(0.0),
    cachedRawRectalTemp(0.0) {}

void SensorModule::begin(EEPROMManager &eepromManager) {
  analogReadResolution(14);
  analogReference(AR_EXTERNAL);  // Bruk AR_DEFAULT hvis ingen ekstern referanse
  eepromManager.loadCalibrationData(EEPROMManager::CALIB_SENSOR_PLATE, plateCalibration);
  eepromManager.loadCalibrationData(EEPROMManager::CALIB_SENSOR_RECTAL, rectalCalibration);
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
  cachedRawCoolingPlateTemp = convertRawToTemp(analogRead(COOLING_PLATE_PIN));
  cachedRawRectalTemp = convertRawToTemp(analogRead(RECTAL_PROBE_PIN));
#endif

  cachedCoolingPlateTemp = applyCalibration(cachedRawCoolingPlateTemp + calibrationOffsetCooling,
                                            plateCalibration);
  cachedRectalTemp = applyCalibration(cachedRawRectalTemp + calibrationOffsetRectal,
                                      rectalCalibration);
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

void SensorModule::setCoolingCalibration(double offset) {
  calibrationOffsetCooling = offset;
}

void SensorModule::setRectalCalibration(double offset) {
  calibrationOffsetRectal = offset;
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

float SensorModule::applyCalibration(float rawTemp, const EEPROMManager::CalibrationData &data) {
  if (data.pointCount == 0) {
    return rawTemp;
  }

  if (data.pointCount == 1) {
    float delta = data.points[0].refValue - data.points[0].rawValue;
    return rawTemp + delta;
  }

  EEPROMManager::CalibrationPoint sortedPoints[5];
  for (uint8_t i = 0; i < data.pointCount && i < 5; ++i) {
    sortedPoints[i] = data.points[i];
  }

  // Simple insertion sort by rawValue
  for (uint8_t i = 1; i < data.pointCount; ++i) {
    EEPROMManager::CalibrationPoint key = sortedPoints[i];
    int j = i - 1;
    while (j >= 0 && sortedPoints[j].rawValue > key.rawValue) {
      sortedPoints[j + 1] = sortedPoints[j];
      --j;
    }
    sortedPoints[j + 1] = key;
  }

  auto interpolate = [](float raw, const EEPROMManager::CalibrationPoint &p1,
                        const EEPROMManager::CalibrationPoint &p2) {
    float denom = (p2.rawValue - p1.rawValue);
    if (denom == 0.0f) {
      return p1.refValue;  // Avoid divide by zero
    }
    float t = (raw - p1.rawValue) / denom;
    return p1.refValue + t * (p2.refValue - p1.refValue);
  };

  if (rawTemp <= sortedPoints[0].rawValue) {
    return interpolate(rawTemp, sortedPoints[0], sortedPoints[1]);
  }

  if (rawTemp >= sortedPoints[data.pointCount - 1].rawValue) {
    return interpolate(rawTemp, sortedPoints[data.pointCount - 2],
                       sortedPoints[data.pointCount - 1]);
  }

  for (uint8_t i = 0; i < data.pointCount - 1; ++i) {
    const EEPROMManager::CalibrationPoint &p1 = sortedPoints[i];
    const EEPROMManager::CalibrationPoint &p2 = sortedPoints[i + 1];
    if (rawTemp >= p1.rawValue && rawTemp <= p2.rawValue) {
      return interpolate(rawTemp, p1, p2);
    }
  }

  return rawTemp;
}

void SensorModule::updateCalibrationData(uint8_t sensorId, const EEPROMManager::CalibrationData &data) {
  if (sensorId == EEPROMManager::CALIB_SENSOR_PLATE) {
    plateCalibration = data;
  } else {
    rectalCalibration = data;
  }
}
