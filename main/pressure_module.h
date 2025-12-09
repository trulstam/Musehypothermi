// pressure_module.h
//
// Breathing detection for Arduino Uno R4 Minima using an Ohmite FSR01BE
// wired as a divider against a 100 kΩ pull-up to the 4.096 V LM4040AIZ
// reference. The ADC is 14-bit (0–16383) and AREF is tied to 4.096 V, so
// all conversions assume that reference. The algorithm is non-blocking and
// expected to run from loop()/task scheduler with ~10–20 ms update periods:
//   raw ADC -> exponential moving average -> slope sign change with
//   hysteresis -> peak counting -> BPM windowing.
// Calibration runs for ~1.5 s in begin()/reset to learn a baseline and
// amplitude-derived threshold; after that detection is continuous.

#ifndef PRESSURE_MODULE_H
#define PRESSURE_MODULE_H

#include "arduino_platform.h"

class PressureModule {
  public:
    PressureModule();

    // Initialize filter state and perform a short baseline calibration.
    void begin();
    // Non-blocking update; sample ADC, filter, detect breaths, update BPM.
    void update();

    void resetBreathMonitor();
    float getBreathRate();

#if SIMULATION_MODE
    void setSimulatedBreathRate(float bpm) { breathsPerMinute = bpm; }
#endif

  private:
#if !SIMULATION_MODE
    static const uint8_t PRESSURE_SENSOR_PIN = A4;  // Divider node (FSR + 100 kΩ)
    static const unsigned long CALIBRATION_DURATION_MS = 1500;  // ~1.5 s baseline
    static const unsigned long MIN_BREATH_INTERVAL_MS = 250;    // reject double peaks
    static const unsigned long BREATH_WINDOW_MS = 10000;        // BPM window length
    static constexpr float ADC_FULL_SCALE = 16383.0f;           // 14-bit ADC range
    static constexpr float VREF_VOLTS = 4.096f;                 // LM4040AIZ-4.1
    static constexpr float FILTER_ALPHA = 0.90f;                // EMA smoothing
    static constexpr float CALIBRATION_FACTOR = 0.35f;          // amplitude -> threshold
    static constexpr float MIN_DELTA_FALLBACK = 8.0f;           // minimal peak delta

    void samplePressure();
    void startCalibration();
    void completeCalibration();
    float adcToVolts(int raw) const { return (raw * VREF_VOLTS) / ADC_FULL_SCALE; }
#endif

    // Common state
    unsigned int breathCount;
    float breathsPerMinute;
    unsigned long breathWindowStart;

#if !SIMULATION_MODE
    float filtered;
    float lastFiltered;
    float lastSlope;

    // Calibration / thresholds
    bool calibrationDone;
    unsigned long calibrationStart;
    float baselineSum;
    unsigned long baselineCount;
    float baseline;
    float calibrationMin;
    float calibrationMax;
    float minPeakDelta;

    unsigned long lastBreathTime;
#endif
};

#endif // PRESSURE_MODULE_H
