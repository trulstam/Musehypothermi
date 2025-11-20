// Musehypothermi Arduino Sensor Module - Class Version
// File: sensor_module.cpp

#include "sensor_module.h"
#include <Arduino.h>
#include <math.h> // For log()

SensorModule::SensorModule()
  : calibrationOffsetCooling(0.0), calibrationOffsetRectal(0.0),
    cachedCoolingPlateTemp(0.0), cachedRectalTemp(0.0) {}

void SensorModule::begin() {
  analogReadResolution(14); // 14-bit ADC
  analogReference(AR_EXTERNAL); // External ref voltage 4.096V
}

void SensorModule::update() {
  cachedCoolingPlateTemp = getCoolingPlateTemp();
  cachedRectalTemp = getRectalTemp();
}

double SensorModule::getCoolingPlateTemp() {
  int rawValue = analogRead(COOLING_PLATE_PIN);
  return convertRawToTemp(rawValue) + calibrationOffsetCooling;
}

double SensorModule::getRectalTemp() {
  int rawValue = analogRead(RECTAL_PROBE_PIN);
  return convertRawToTemp(rawValue) + calibrationOffsetRectal;
}

void SensorModule::setCoolingCalibration(double offset) {
  calibrationOffsetCooling = offset;
}

void SensorModule::setRectalCalibration(double offset) {
  calibrationOffsetRectal = offset;
}

double SensorModule::convertRawToTemp(int raw) {
  // Sanity check
  if (raw <= 0 || raw >= 16383) {
    Serial.println("{\"err\": \"Sensor raw value out of range\"}");
    return -273.15; // Invalid temp marker
  }

  double voltage = (raw / 16383.0) * 4.096; // 14-bit ADC scaling
  double resistance = (voltage / (4.096 - voltage)) * 10000.0; // Assume 10k pull-up
  double tempK = 1.0 / (1.0 / 298.15 + (1.0 / 3988.0) * log(resistance / 10000.0));
  return tempK - 273.15; // Kelvin to Celsius
}
