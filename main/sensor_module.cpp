// ===================== sensor_module.cpp =====================
#include "sensor_module.h"
#include <Arduino.h>
#include <math.h>
#include "pid_module_asymmetric.h"
#include "system_config.h"

extern AsymmetricPIDModule pid;

namespace {
double mapDouble(double x, double in_min, double in_max, double out_min, double out_max) {
  if (in_max - in_min == 0.0) {
    return out_min;
  }
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}
}

static double coolingPlateTemp = 22.0;
static double rectalTemp = 37.0;

const double plateThermalMass = 0.3;
const double plateSpecificHeat = 900.0;
const double plateCoolingLoss = 0.01;

const double rectalThermalMass = 0.03;
const double rectalSpecificHeat = 3470.0;
const double rectalCoupling = 0.02;

SensorModule::SensorModule()
  : calibrationOffsetCooling(0.0), calibrationOffsetRectal(0.0),
    cachedCoolingPlateTemp(0.0), cachedRectalTemp(0.0) {}

void SensorModule::begin() {
  analogReadResolution(14);
  analogReference(AR_EXTERNAL);  // Bruk AR_DEFAULT hvis ingen ekstern referanse
}

void SensorModule::update() {
  if (USE_SIMULATION) {
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

    double metabolicPower = mapDouble(rectalTemp, 14.0, 37.0, 0.01, 0.21);

    double deltaQRectal = rectalCoupling * (coolingPlateTemp - rectalTemp) * deltaTime
                        + metabolicPower * deltaTime;
    double deltaTempRectal = deltaQRectal / (rectalThermalMass * rectalSpecificHeat);
    rectalTemp += deltaTempRectal;

    coolingPlateTemp = constrain(coolingPlateTemp, -10.0, 50.0);
    rectalTemp = constrain(rectalTemp, 14.0, 45.0);

    int adcNoiseRaw = analogRead(A3);
    double noise = mapDouble(static_cast<double>(adcNoiseRaw), 0.0, 16383.0, -0.05, 0.05);

    cachedCoolingPlateTemp = coolingPlateTemp + calibrationOffsetCooling + noise;
    cachedRectalTemp = rectalTemp + calibrationOffsetRectal + noise;
  } else {
    int rawCooling = analogRead(COOLING_PLATE_PIN);
    int rawRectal = analogRead(RECTAL_PROBE_PIN);

    double coolingTemp = convertRawToTemp(rawCooling);
    double rectalTemperature = convertRawToTemp(rawRectal);

    cachedCoolingPlateTemp = coolingTemp + calibrationOffsetCooling;
    cachedRectalTemp = rectalTemperature + calibrationOffsetRectal;
  }
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

double SensorModule::convertRawToTemp(int raw) {
  if (raw <= 0 || raw >= 16383) {
    Serial.println("{\"err\": \"Sensor raw value out of range\"}");
    return -273.15;
  }

  double voltage = (raw / 16383.0) * 4.096;
  double resistance = (voltage / (4.096 - voltage)) * 10000.0;
  double tempK = 1.0 / (1.0 / 298.15 + (1.0 / 3988.0) * log(resistance / 10000.0));
  return tempK - 273.15;
}
