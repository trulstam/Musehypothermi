// ===================== pressure_module.cpp =====================
#include "pressure_module.h"

#include "arduino_platform.h"
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

  const double tempThreshold = 16.0;
  const double tempMin = 14.0;
  const double maxTemp = 37.0;
  const double maxBreaths = 150.0;
  const double minBreathsAtThreshold = 1.5;

  bool apneaCondition = rectalTemp <= tempMin;

  if (apneaCondition) {
    breathsPerMinute = 0.0;
  } else if (rectalTemp < tempThreshold) {
    double scale = (rectalTemp - tempMin) / (tempThreshold - tempMin);
    breathsPerMinute = minBreathsAtThreshold * scale * scale;
  } else {
    double clampedTemp = min(rectalTemp, maxTemp);
    double slope = (maxBreaths - minBreathsAtThreshold) / (maxTemp - tempThreshold);
    breathsPerMinute = minBreathsAtThreshold + slope * (clampedTemp - tempThreshold);
  }

  int adcNoiseRaw = analogRead(A4);
  double normalizedNoise = static_cast<double>(adcNoiseRaw) / 16383.0;
  double noise = -0.5 + normalizedNoise;

  if (!apneaCondition) {
    breathsPerMinute += noise;
    breathsPerMinute = constrain(breathsPerMinute, 0.0, maxBreaths);
    if (breathsPerMinute < 0.1) {
      breathsPerMinute = 0.1;
    }
  }
}

float PressureModule::getBreathRate() {
  return breathsPerMinute;
}

void PressureModule::resetBreathMonitor() {
  breathCount = 0;
  breathsPerMinute = 150.0;
  breathWindowStart = millis();
}
