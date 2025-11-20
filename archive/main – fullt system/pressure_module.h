// pressure_module.h

#ifndef PRESSURE_MODULE_H
#define PRESSURE_MODULE_H

#include <Arduino.h>

class PressureModule {
  public:
    PressureModule();

    void begin();
    void update();

    void resetBreathMonitor();
    float getBreathRate();

  private:
    void samplePressure();
    void sendPressureData(); // Valgfri / Hvis du vil bruke

    static const uint8_t BUFFER_SIZE = 32;
    uint16_t pressureBuffer[BUFFER_SIZE];
    uint8_t bufferIndex;

    int lastPressureSample;
    uint8_t breathThreshold;

    // TELLING AV PUST:
    unsigned int breathCount;
    float breathsPerMinute;

    // NYTT felt for å lagre start-tid for BPM-vindu:
    unsigned long breathWindowStart;  // <--- Legg denne til

    // (Eventuelt kommenter bort failsafe)
    // static const unsigned long BREATH_FAILSAFE_TIMEOUT = 10000;  // ms
};

#endif // PRESSURE_MODULE_H
