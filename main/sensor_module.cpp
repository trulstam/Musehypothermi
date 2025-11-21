// ===================== sensor_module.cpp =====================
#include "sensor_module.h"
#include <Arduino.h>
#include <math.h>
#include "pid_module_asymmetric.h"

extern AsymmetricPIDModule pid;

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

  cachedCoolingPlateTemp = coolingPlateTemp + calibrationOffsetCooling + noise;
  cachedRectalTemp = rectalTemp + calibrationOffsetRectal + noise;
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
