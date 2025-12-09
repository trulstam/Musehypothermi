// pressure_module.h
//
// Breathing detection using an Ohmite FSR01BE force sensor on Arduino Uno R4
// Minima. The sensor forms a divider with a 100 kΩ pull-up to the 4.096 V
// reference feeding both the ADC (14-bit, 0–16383) and the sensor. Each call to
// update() samples A4, applies an exponential moving average, performs a short
// automatic calibration (~1.5 s) to learn the baseline and dynamic threshold,
// then detects breaths via slope sign changes and amplitude checks. A 10-second
// rolling window computes breaths-per-minute (BPM). The implementation is
// non-blocking and intended for periodic calls (e.g., from loop() or a task
// scheduler) at roughly 10–20 ms intervals.

#ifndef PRESSURE_MODULE_H
#define PRESSURE_MODULE_H

#include "arduino_platform.h"

class PressureModule {
  public:
    PressureModule();

    void begin();
    void update();

    float getBreathRate();
    void resetBreathMonitor();

    uint16_t getRawAdc() const;
    float    getFiltered() const;
    float    getBaseline() const;
    float    getDeviation() const;
    float    getMinPeakDelta() const;
    bool     getLastBreathDetected() const;

  private:
    static const uint8_t PRESSURE_SENSOR_PIN = A4;
    static const unsigned long CALIBRATION_DURATION_MS = 1500;
    static const unsigned long MIN_BREATH_INTERVAL_MS = 250;
    static const unsigned long BREATH_WINDOW_MS = 10000;
    static constexpr float FILTER_ALPHA = 0.90f;
    static constexpr float BASELINE_DRIFT_ALPHA = 0.999f;
    static constexpr float MIN_PEAK_DELTA = 8.0f;
    static constexpr float PEAK_SCALE = 0.30f;

    void sampleSensor();
    void startCalibration();
    void completeCalibration();

    // Breath windowing
    unsigned int breathCount;
    float breathsPerMinute;
    unsigned long breathWindowStart;

    // ADC/filtering state
    uint16_t rawAdc;
    float filteredValue;
    float lastFiltered;
    float lastSlope;

    // Calibration
    bool calibrationDone;
    unsigned long calibrationStart;
    float baselineSum;
    unsigned long baselineCount;
    float calibrationMin;
    float calibrationMax;
    float baselineValue;
    float deviationValue;
    float thresholdValue;

    // Detection
    unsigned long lastBreathTime;
    bool lastBreathDetectedFlag;
};

#endif // PRESSURE_MODULE_H
