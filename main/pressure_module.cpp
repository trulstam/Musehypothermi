// ===================== pressure_module.cpp =====================
#include "pressure_module.h"
#include <Arduino.h>
#include "sensor_module.h"

extern SensorModule sensors;

PressureModule::PressureModule()
  : bufferIndex(0), lastPressureSample(0),
    breathThreshold(5), breathCount(0), breathsPerMinute(0),
    breathWindowStart(0) {}

void PressureModule::begin() {
  breathsPerMinute = 150.0;
  breathWindowStart = millis();
}

void PressureModule::update() {
  static unsigned long lastUpdate = millis();
  unsigned long now = millis();
  double deltaTime = (now - lastUpdate) / 1000.0;
  if (deltaTime <= 0.0) return;
  lastUpdate = now;

  double rectalTemp = sensors.getRectalTemp();

  double tempThreshold = 16.0;
  double tempMin = 14.0;

  if (rectalTemp <= tempMin) {
      breathsPerMinute = 0.0;
  } else if (rectalTemp < tempThreshold) {
      double scale = (rectalTemp - tempMin) / (tempThreshold - tempMin);
      breathsPerMinute = 1.5 * scale * scale;
  } else {
      double scale = (rectalTemp - tempThreshold) / (37.0 - tempThreshold);
      breathsPerMinute = 1.5 + scale * (150.0 - 1.5);
  }

  int adcNoiseRaw = analogRead(A4);
  double noise = ((static_cast<double>(adcNoiseRaw) / 16383.0) * 1.0) - 0.5;

  breathsPerMinute += noise;
  if (breathsPerMinute < 0.1) {
      breathsPerMinute = 0.1;
  }
  breathsPerMinute = constrain(breathsPerMinute, 0.1, 150.0);
}

float PressureModule::getBreathRate() {
  return breathsPerMinute;
}

void PressureModule::resetBreathMonitor() {
  breathCount = 0;
  breathsPerMinute = 150.0;
  breathWindowStart = millis();
}
