// ===================== pressure_module.cpp =====================
#include "pressure_module.h"

#include "arduino_platform.h"
#include "sensor_module.h"

extern SensorModule sensors;

#if !SIMULATION_MODE
#define PRESSURE_SENSOR_PIN A0
static const unsigned long BREATH_WINDOW_MS = 10000;
#endif

PressureModule::PressureModule()
  : bufferIndex(0), lastPressureSample(0),
    breathThreshold(5), breathCount(0), breathsPerMinute(0),
    breathWindowStart(0) {}

void PressureModule::begin() {
  breathWindowStart = millis();

#if SIMULATION_MODE
  breathsPerMinute = 150.0;
#else
  lastPressureSample = analogRead(PRESSURE_SENSOR_PIN);
  bufferIndex = 0;
  breathCount = 0;
  breathsPerMinute = 0;
#endif
}

void PressureModule::update() {
#if SIMULATION_MODE
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
#else
  samplePressure();
#endif
}

#if !SIMULATION_MODE
void PressureModule::samplePressure() {
  int raw = analogRead(PRESSURE_SENSOR_PIN);

  if (raw <= 0 || raw >= 16383) {
    raw = 0;
  }

  if (abs(raw - lastPressureSample) > breathThreshold) {
    breathCount++;
    lastPressureSample = raw;
  }

  unsigned long now = millis();
  if (now - breathWindowStart >= BREATH_WINDOW_MS) {
    breathsPerMinute = breathCount * 6.0f;
    breathCount = 0;
    breathWindowStart = now;
  }
}

void PressureModule::sendPressureData() {
  // Optional serial dump disabled to keep firmware quiet on hardware
}
#endif

float PressureModule::getBreathRate() {
  return breathsPerMinute;
}

void PressureModule::resetBreathMonitor() {
  breathWindowStart = millis();

#if SIMULATION_MODE
  breathCount = 0;
  breathsPerMinute = 150.0;
#else
  lastPressureSample = analogRead(PRESSURE_SENSOR_PIN);
  breathCount = 0;
  breathsPerMinute = 0;
#endif
}
