// ===================== pressure_module.cpp =====================
// Implementation details:
// - Hardware: Ohmite FSR01BE with 100 kΩ pull-up to a 4.096 V LM4040AIZ-4.1
//   precision reference feeding AREF and the divider. The Uno R4 Minima ADC
//   is 14-bit (0–16383). All ADC math assumes VREF = 4.096 V.
// - Sampling: update() is expected every 10–20 ms (no slower than 50 ms).
//   Each call grabs one analogRead() on A4.
// - Filtering: exponential moving average with alpha=0.90 retains stability
//   while following typical breathing waveforms.
// - Detection: slope zero-crossing from positive to negative with hysteresis
//   (filtered > baseline + minPeakDelta) and a minimum spacing guard to avoid
//   double-counting noise. BPM uses a 10 s window to limit jitter.
// - Calibration: first ~1.5 s collects filtered samples to learn baseline and
//   amplitude. Threshold derives from amplitude * 0.35 with an 8-count floor.
//   After calibration the detector runs automatically without blocking.

#include "pressure_module.h"

#include "arduino_platform.h"
#include "sensor_module.h"

extern SensorModule sensors;

PressureModule::PressureModule()
    : breathCount(0), breathsPerMinute(0.0f), breathWindowStart(0)
#if !SIMULATION_MODE
    , filtered(0.0f), lastFiltered(0.0f), lastSlope(0.0f), calibrationDone(false),
      calibrationStart(0), baselineSum(0.0f), baselineCount(0), baseline(0.0f),
      calibrationMin(0.0f), calibrationMax(0.0f), minPeakDelta(MIN_DELTA_FALLBACK),
      lastBreathTime(0)
#endif
{
}

void PressureModule::begin() {
  breathCount = 0;
  breathsPerMinute = 0.0f;
  breathWindowStart = millis();

#if SIMULATION_MODE
  breathsPerMinute = 150.0f;
#else
  startCalibration();
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
void PressureModule::startCalibration() {
  calibrationDone = false;
  calibrationStart = millis();
  baselineSum = 0.0f;
  baselineCount = 0;
  calibrationMin = 1e9f;
  calibrationMax = -1e9f;
  minPeakDelta = MIN_DELTA_FALLBACK;
  lastSlope = 0.0f;

  int raw = analogRead(PRESSURE_SENSOR_PIN);
  filtered = static_cast<float>(raw);
  lastFiltered = filtered;
  baseline = filtered;
  lastBreathTime = calibrationStart;
}

void PressureModule::completeCalibration() {
  if (baselineCount == 0) {
    baseline = filtered;
    calibrationMin = filtered;
    calibrationMax = filtered;
  } else {
    baseline = baselineSum / static_cast<float>(baselineCount);
  }

  float amplitude = calibrationMax - calibrationMin;
  if (amplitude < 0.0f) amplitude = 0.0f;
  float derivedDelta = amplitude * CALIBRATION_FACTOR;
  if (derivedDelta < MIN_DELTA_FALLBACK) {
    derivedDelta = MIN_DELTA_FALLBACK;
  }
  minPeakDelta = derivedDelta;
  calibrationDone = true;
}

void PressureModule::samplePressure() {
  unsigned long now = millis();
  int raw = analogRead(PRESSURE_SENSOR_PIN);

  lastFiltered = filtered;
  filtered = (FILTER_ALPHA * filtered) + ((1.0f - FILTER_ALPHA) * static_cast<float>(raw));

  if (!calibrationDone) {
    baselineSum += filtered;
    baselineCount++;
    if (filtered < calibrationMin) calibrationMin = filtered;
    if (filtered > calibrationMax) calibrationMax = filtered;

    if (now - calibrationStart >= CALIBRATION_DURATION_MS) {
      completeCalibration();
    }
    return;
  }

  // Slow baseline drift compensation.
  baseline = (0.999f * baseline) + (0.001f * filtered);

  float slope = filtered - lastFiltered;
  bool risingToFalling = (lastSlope > 0.0f) && (slope <= 0.0f);
  lastSlope = slope;

  bool aboveThreshold = filtered > (baseline + minPeakDelta);
  bool intervalOk = (now - lastBreathTime) >= MIN_BREATH_INTERVAL_MS;

  if (risingToFalling && aboveThreshold && intervalOk) {
    breathCount++;
    lastBreathTime = now;
  }

  unsigned long windowElapsed = now - breathWindowStart;
  if (windowElapsed >= BREATH_WINDOW_MS) {
    if (windowElapsed > 0) {
      breathsPerMinute = breathCount * (60000.0f / static_cast<float>(windowElapsed));
    } else {
      breathsPerMinute = 0.0f;
    }
    breathCount = 0;
    breathWindowStart = now;
  }
}
#endif

float PressureModule::getBreathRate() {
  return breathsPerMinute;
}

void PressureModule::resetBreathMonitor() {
  breathCount = 0;
  breathsPerMinute = 0.0f;
  breathWindowStart = millis();

#if SIMULATION_MODE
  breathsPerMinute = 150.0f;
#else
  startCalibration();
#endif
}
