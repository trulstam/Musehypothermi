// ===================== pressure_module.cpp =====================
// FSR-based breathing detector for Arduino Uno R4 Minima.
// - Hardware: Ohmite FSR01BE against 100 kΩ pull-up to the shared 4.096 V
//   reference (AREF). The ADC is 14-bit (0–16383).
// - Sampling: update() reads A4 each invocation (expected ~10–20 ms cadence).
// - Filtering: exponential moving average with alpha ≈ 0.90 smooths noise while
//   following breathing waveforms.
// - Calibration: first ~1.5 s after begin()/reset gathers filtered samples to
//   learn baseline and peak amplitude. Threshold = amplitude * 0.30 with an
//   8-count floor. Baseline is tracked slowly thereafter to absorb drift.
// - Detection: a breath is counted when the filtered slope switches from
//   positive to negative, the sample sits above baseline + threshold, and the
//   minimum breath spacing (250 ms) has elapsed.
// - BPM: a 10 s rolling window computes breaths-per-minute.

#include "pressure_module.h"

PressureModule::PressureModule()
    : breathCount(0), breathsPerMinute(0.0f), breathWindowStart(0),
      lastRaw(0), filtered(0.0f), lastFiltered(0.0f), lastSlope(0.0f),
      calibrationDone(false), calibrationStart(0), baselineSum(0.0f),
      baselineCount(0), calibrationMin(0.0f), calibrationMax(0.0f),
      baseline(0.0f), minPeakDelta(MIN_PEAK_DELTA), lastBreathTime(0) {}

void PressureModule::begin() {
  breathCount = 0;
  breathsPerMinute = 0.0f;
  breathWindowStart = millis();
  startCalibration();
}

void PressureModule::update() {
  sampleSensor();
}

void PressureModule::sampleSensor() {
  unsigned long now = millis();
  lastRaw = analogRead(PRESSURE_SENSOR_PIN);

  lastFiltered = filtered;
  filtered = (FILTER_ALPHA * filtered) + ((1.0f - FILTER_ALPHA) * static_cast<float>(lastRaw));

  if (!calibrationDone) {
    baselineSum += filtered;
    baselineCount++;
    if (baselineCount == 1) {
      calibrationMin = filtered;
      calibrationMax = filtered;
    } else {
      if (filtered < calibrationMin) calibrationMin = filtered;
      if (filtered > calibrationMax) calibrationMax = filtered;
    }

    if (now - calibrationStart >= CALIBRATION_DURATION_MS) {
      completeCalibration();
      lastBreathTime = now;
    }
    return;
  }

  baseline = (BASELINE_DRIFT_ALPHA * baseline) + ((1.0f - BASELINE_DRIFT_ALPHA) * filtered);

  float slope = filtered - lastFiltered;
  bool zeroCross = (lastSlope > 0.0f) && (slope <= 0.0f);
  lastSlope = slope;

  bool aboveThreshold = filtered > (baseline + minPeakDelta);
  bool spacingOk = (now - lastBreathTime) >= MIN_BREATH_INTERVAL_MS;

  if (zeroCross && aboveThreshold && spacingOk) {
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

void PressureModule::startCalibration() {
  calibrationDone = false;
  calibrationStart = millis();
  baselineSum = 0.0f;
  baselineCount = 0;
  calibrationMin = 0.0f;
  calibrationMax = 0.0f;
  baseline = 0.0f;
  minPeakDelta = MIN_PEAK_DELTA;
  lastSlope = 0.0f;

  lastRaw = analogRead(PRESSURE_SENSOR_PIN);
  filtered = static_cast<float>(lastRaw);
  lastFiltered = filtered;
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

  float derivedDelta = amplitude * PEAK_SCALE;
  if (derivedDelta < MIN_PEAK_DELTA) {
    derivedDelta = MIN_PEAK_DELTA;
  }

  minPeakDelta = derivedDelta;
  calibrationDone = true;
}

float PressureModule::getBreathRate() {
  return breathsPerMinute;
}

void PressureModule::resetBreathMonitor() {
  breathCount = 0;
  breathsPerMinute = 0.0f;
  breathWindowStart = millis();
  startCalibration();
}
