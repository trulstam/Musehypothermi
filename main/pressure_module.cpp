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
    : breathsPerMinute(0.0f), breathHead(0), breathTail(0),
      rawAdc(0), filteredValue(0.0f), lastFiltered(0.0f), lastSlope(0.0f),
      lastDeviation(0.0f),
      calibrationDone(false), calibrationStart(0), baselineSum(0.0f),
      baselineCount(0), calibrationMin(0.0f), calibrationMax(0.0f),
      baselineValue(0.0f), deviationValue(0.0f), thresholdValue(MIN_PEAK_DELTA),
      lastBreathTime(0), lastBreathDetectedFlag(false) {}

void PressureModule::begin() {
  breathsPerMinute = 0.0f;
  breathHead = 0;
  breathTail = 0;
  startCalibration();
}

void PressureModule::update() {
  sampleSensor();
}

void PressureModule::sampleSensor() {
  unsigned long now = millis();
  lastBreathDetectedFlag = false;
  rawAdc = analogRead(PRESSURE_SENSOR_PIN);

  lastFiltered = filteredValue;
  filteredValue =
      (FILTER_ALPHA * filteredValue) + ((1.0f - FILTER_ALPHA) * static_cast<float>(rawAdc));

  if (!calibrationDone) {
    baselineSum += filteredValue;
    baselineCount++;
    if (baselineCount == 1) {
      calibrationMin = filteredValue;
      calibrationMax = filteredValue;
    } else {
      if (filteredValue < calibrationMin) calibrationMin = filteredValue;
      if (filteredValue > calibrationMax) calibrationMax = filteredValue;
    }

    if (now - calibrationStart >= CALIBRATION_DURATION_MS) {
      completeCalibration();
      lastBreathTime = now;
    }
    return;
  }

  baselineValue = (BASELINE_DRIFT_ALPHA * baselineValue) +
                  ((1.0f - BASELINE_DRIFT_ALPHA) * filteredValue);
  deviationValue = baselineValue - filteredValue;

  float deviation = deviationValue;

  float slope = deviation - lastDeviation;
  bool zeroCross = (lastSlope > 0.0f) && (slope <= 0.0f);
  lastSlope = slope;
  lastDeviation = deviation;

  bool aboveThreshold = deviation > thresholdValue;
  bool spacingOk = (now - lastBreathTime) >= MIN_BREATH_INTERVAL_MS;

  if (zeroCross && aboveThreshold && spacingOk) {
    breathTimestamps[breathHead] = now;
    uint8_t nextHead = static_cast<uint8_t>((breathHead + 1) % MAX_BREATH_EVENTS);
    if (nextHead == breathTail) {
      breathTail = static_cast<uint8_t>((breathTail + 1) % MAX_BREATH_EVENTS);
    }
    breathHead = nextHead;
    lastBreathTime = now;
    lastBreathDetectedFlag = true;
  }

  while (breathTail != breathHead && (now - breathTimestamps[breathTail]) > BREATH_WINDOW_MS) {
    breathTail = static_cast<uint8_t>((breathTail + 1) % MAX_BREATH_EVENTS);
  }

  unsigned int recentCount = 0;
  uint8_t idx = breathTail;
  while (idx != breathHead) {
    unsigned long timestamp = breathTimestamps[idx];
    if ((now - timestamp) <= BREATH_WINDOW_MS) {
      recentCount++;
    }
    idx = static_cast<uint8_t>((idx + 1) % MAX_BREATH_EVENTS);
  }

  if (recentCount > 0) {
    breathsPerMinute =
        recentCount * (60000.0f / static_cast<float>(BREATH_WINDOW_MS));
  } else {
    breathsPerMinute = 0.0f;
  }
}

void PressureModule::startCalibration() {
  calibrationDone = false;
  calibrationStart = millis();
  baselineSum = 0.0f;
  baselineCount = 0;
  calibrationMin = 0.0f;
  calibrationMax = 0.0f;
  baselineValue = 0.0f;
  deviationValue = 0.0f;
  thresholdValue = MIN_PEAK_DELTA;
  lastSlope = 0.0f;
  lastDeviation = 0.0f;

  rawAdc = analogRead(PRESSURE_SENSOR_PIN);
  filteredValue = static_cast<float>(rawAdc);
  lastFiltered = filteredValue;
}

void PressureModule::completeCalibration() {
  if (baselineCount == 0) {
    baselineValue = filteredValue;
    calibrationMin = filteredValue;
    calibrationMax = filteredValue;
  } else {
    baselineValue = baselineSum / static_cast<float>(baselineCount);
  }

  float amplitude = calibrationMax - calibrationMin;
  if (amplitude < 0.0f) amplitude = 0.0f;

  float derivedDelta = amplitude * PEAK_SCALE;
  if (derivedDelta < MIN_PEAK_DELTA) {
    derivedDelta = MIN_PEAK_DELTA;
  }

  thresholdValue = derivedDelta;
  calibrationDone = true;
}

float PressureModule::getBreathRate() {
  return breathsPerMinute;
}

void PressureModule::resetBreathMonitor() {
  breathsPerMinute = 0.0f;
  breathHead = 0;
  breathTail = 0;
  startCalibration();
}

uint16_t PressureModule::getRawAdc() const { return rawAdc; }

float PressureModule::getFiltered() const { return filteredValue; }

float PressureModule::getBaseline() const { return baselineValue; }

float PressureModule::getDeviation() const { return deviationValue; }

float PressureModule::getMinPeakDelta() const { return thresholdValue; }

bool PressureModule::getLastBreathDetected() const { return lastBreathDetectedFlag; }
