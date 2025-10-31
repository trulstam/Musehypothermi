// ===================== pressure_module.cpp =====================
#include "pressure_module.h"
#include <Arduino.h>
#include <math.h>
#include "sensor_module.h"
#include "system_config.h"

extern SensorModule sensors;

namespace {
constexpr unsigned long kBreathWindowMs = 10000UL;
constexpr unsigned long kMinBreathIntervalMs = 500UL;
}

PressureModule::PressureModule()
  : bufferIndex(0), lastPressureSample(0),
    breathThreshold(5), breathCount(0), breathsPerMinute(0),
    breathWindowStart(0), lastBreathEventMillis(0), hasValidBreathRate(false) {}

void PressureModule::begin() {
  bufferIndex = 0;
  breathCount = 0;
  breathsPerMinute = 0.0f;
  unsigned long now = millis();
  breathWindowStart = now;
  lastBreathEventMillis = now;
  hasValidBreathRate = false;

  if (USE_SIMULATION) {
    breathsPerMinute = 150.0f;
    hasValidBreathRate = true;
  } else {
    lastPressureSample = analogRead(PRESSURE_SENSOR_PIN);
  }
}

void PressureModule::update() {
  if (USE_SIMULATION) {
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
      breathsPerMinute = 0.0f;
    } else if (rectalTemp < tempThreshold) {
      double scale = (rectalTemp - tempMin) / (tempThreshold - tempMin);
      breathsPerMinute = static_cast<float>(minBreathsAtThreshold * scale * scale);
    } else {
      double clampedTemp = min(rectalTemp, maxTemp);
      double slope = (maxBreaths - minBreathsAtThreshold) / (maxTemp - tempThreshold);
      breathsPerMinute = static_cast<float>(minBreathsAtThreshold + slope * (clampedTemp - tempThreshold));
    }

    int adcNoiseRaw = analogRead(A4);
    double normalizedNoise = static_cast<double>(adcNoiseRaw) / 16383.0;
    double noise = -0.5 + normalizedNoise;

    if (!apneaCondition) {
      breathsPerMinute += static_cast<float>(noise);
      breathsPerMinute = constrain(breathsPerMinute, 0.0f, static_cast<float>(maxBreaths));
      if (breathsPerMinute < 0.1f) {
        breathsPerMinute = 0.1f;
      }
    }

    hasValidBreathRate = true;
  } else {
    samplePressure();
  }
}

void PressureModule::samplePressure() {
  int raw = analogRead(PRESSURE_SENSOR_PIN);
  unsigned long now = millis();

  if (raw <= 0 || raw >= 16383) {
    raw = 0;
  }

  if (abs(raw - lastPressureSample) > breathThreshold) {
    if (now - lastBreathEventMillis >= kMinBreathIntervalMs) {
      breathCount++;
      lastBreathEventMillis = now;
    }
    lastPressureSample = raw;
  }

  unsigned long windowElapsed = now - breathWindowStart;
  if (windowElapsed >= kBreathWindowMs) {
    if (windowElapsed > 0) {
      breathsPerMinute = static_cast<float>(breathCount) * (60000.0f / windowElapsed);
    } else {
      breathsPerMinute = 0.0f;
    }
    breathCount = 0;
    breathWindowStart = now;
    hasValidBreathRate = true;
  }

  // Optional circular buffer logging left disabled by default.
}

void PressureModule::sendPressureData() {
  // Reserved for future serial debug output.
}

void PressureModule::resetBreathMonitor() {
  lastPressureSample = analogRead(PRESSURE_SENSOR_PIN);
  breathCount = 0;
  breathsPerMinute = 0.0f;
  unsigned long now = millis();
  breathWindowStart = now;
  lastBreathEventMillis = now;
  hasValidBreathRate = false;
}

float PressureModule::getBreathRate() {
  return hasValidBreathRate ? breathsPerMinute : NAN;
}
