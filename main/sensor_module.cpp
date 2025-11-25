// ===================== sensor_module.cpp =====================
#include "sensor_module.h"

#include "arduino_platform.h"
#include <math.h>
#include <string.h>
#include "eeprom_manager.h"
#include "pid_module_asymmetric.h"

extern AsymmetricPIDModule pid;
extern EEPROMManager eeprom;

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
  : plateCalCount(0), rectalCalCount(0), eepromManagerPointer(nullptr),
    calibrationOffsetCooling(0.0), calibrationOffsetRectal(0.0),
    cachedCoolingPlateTemp(0.0), cachedRectalTemp(0.0),
    lastRawCoolingPlateTemp(0.0), lastRawRectalTemp(0.0) {}

void SensorModule::begin() {
  eepromManagerPointer = &eeprom;

  analogReadResolution(14);
  analogReference(AR_EXTERNAL);  // Bruk AR_DEFAULT hvis ingen ekstern referanse

  if (eepromManagerPointer) {
    eepromManagerPointer->loadPlateCalibration(plateCalTable, plateCalCount);
    eepromManagerPointer->loadRectalCalibration(rectalCalTable, rectalCalCount);
  } else {
    plateCalCount = 0;
    rectalCalCount = 0;
  }
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

  double rawPlate = coolingPlateTemp + noise;
  double rawRectal = rectalTemp + noise;

  lastRawCoolingPlateTemp = rawPlate;
  lastRawRectalTemp = rawRectal;

  cachedCoolingPlateTemp = applyCalibration(rawPlate, plateCalTable, plateCalCount) +
                          calibrationOffsetCooling;  // Offset kept for compatibility
  cachedRectalTemp = applyCalibration(rawRectal, rectalCalTable, rectalCalCount) +
                     calibrationOffsetRectal;
#else
  double rawPlate = convertRawToTemp(analogRead(COOLING_PLATE_PIN));
  double rawRectal = convertRawToTemp(analogRead(RECTAL_PROBE_PIN));

  lastRawCoolingPlateTemp = rawPlate;
  lastRawRectalTemp = rawRectal;

  cachedCoolingPlateTemp = applyCalibration(rawPlate, plateCalTable, plateCalCount) +
                           calibrationOffsetCooling;  // Table is primary calibration
  cachedRectalTemp = applyCalibration(rawRectal, rectalCalTable, rectalCalCount) +
                     calibrationOffsetRectal;
#endif
}

double SensorModule::getCoolingPlateTemp() {
  return cachedCoolingPlateTemp;
}

double SensorModule::getRectalTemp() {
  return cachedRectalTemp;
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

bool SensorModule::addCalibrationPoint(const char* sensorName, float referenceTemp) {
  if (!sensorName) return false;

  CalibrationPoint* table = nullptr;
  uint8_t* countPtr = nullptr;
  double measured = 0.0;

  if (strcmp(sensorName, "plate") == 0) {
    table = plateCalTable;
    countPtr = &plateCalCount;
    measured = lastRawCoolingPlateTemp;
  } else if (strcmp(sensorName, "rectal") == 0) {
    table = rectalCalTable;
    countPtr = &rectalCalCount;
    measured = lastRawRectalTemp;
  } else {
    return false;
  }

  if (*countPtr >= MAX_CAL_POINTS) {
    return false;
  }

  uint8_t idx = *countPtr;
  table[idx].measured = static_cast<float>(measured);
  table[idx].reference = referenceTemp;
  (*countPtr)++;

  for (uint8_t i = 0; i + 1 < *countPtr; ++i) {
    for (uint8_t j = i + 1; j < *countPtr; ++j) {
      if (table[j].measured < table[i].measured) {
        CalibrationPoint tmp = table[i];
        table[i] = table[j];
        table[j] = tmp;
      }
    }
  }

  return true;
}

bool SensorModule::commitCalibration(const char* sensorName,
                                     const char* operatorName,
                                     uint32_t timestamp) {
  if (!eepromManagerPointer || !sensorName) {
    return false;
  }

  const char* op = operatorName ? operatorName : "";
  if (strcmp(sensorName, "plate") == 0) {
    return eepromManagerPointer->savePlateCalibration(plateCalTable,
                                                      plateCalCount,
                                                      op,
                                                      timestamp);
  } else if (strcmp(sensorName, "rectal") == 0) {
    return eepromManagerPointer->saveRectalCalibration(rectalCalTable,
                                                       rectalCalCount,
                                                       op,
                                                       timestamp);
  } else if (strcmp(sensorName, "both") == 0) {
    bool ok1 = eepromManagerPointer->savePlateCalibration(plateCalTable,
                                                          plateCalCount,
                                                          op,
                                                          timestamp);
    bool ok2 = eepromManagerPointer->saveRectalCalibration(rectalCalTable,
                                                           rectalCalCount,
                                                           op,
                                                           timestamp);
    return ok1 && ok2;
  }
  return false;
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

// Applies table-based calibration using linear interpolation of (measured, reference) pairs.
double SensorModule::applyCalibration(double rawTemp,
                                      const CalibrationPoint* table,
                                      uint8_t count) const {
  if (count == 0 || !table) {
    return rawTemp;
  }

  if (rawTemp <= table[0].measured) {
    return table[0].reference;
  }
  if (rawTemp >= table[count - 1].measured) {
    return table[count - 1].reference;
  }

  for (uint8_t i = 0; i + 1 < count; ++i) {
    float m0 = table[i].measured;
    float m1 = table[i + 1].measured;
    if (m1 <= m0) {
      continue;
    }

    if (rawTemp >= m0 && rawTemp <= m1) {
      float r0 = table[i].reference;
      float r1 = table[i + 1].reference;
      float t = (rawTemp - m0) / (m1 - m0);
      return r0 + t * (r1 - r0);
    }
  }

  return rawTemp;
}
