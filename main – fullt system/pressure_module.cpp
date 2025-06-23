// Musehypothermi Arduino Pressure Module - Revised Version
// File: pressure_module.cpp

#include "pressure_module.h"
#include <Arduino.h>

#define PRESSURE_SENSOR_PIN A0  // Or your actual pin

// Vi bruker et 10 sek vindu for BPM:
static const unsigned long BREATH_WINDOW_MS = 10000; // 10 sek

PressureModule::PressureModule()
  : bufferIndex(0), lastPressureSample(0),
    breathThreshold(5), breathCount(0), breathsPerMinute(0),
    breathWindowStart(0)
{
  // Fjerner lastBreathActivity og failsafe-check helt
}

void PressureModule::begin() {
  // Les første trykkverdi for referanse
  lastPressureSample = analogRead(PRESSURE_SENSOR_PIN);

  // Nullstiller buffere og tellere
  bufferIndex = 0;
  breathCount = 0;
  breathsPerMinute = 0;
  breathWindowStart = millis();
}

void PressureModule::update() {
  samplePressure();
  // Fjerner failsafe-check om "No breathing detected" her
}

void PressureModule::samplePressure() {
  int raw = analogRead(PRESSURE_SENSOR_PIN);

  // Hvis rå er utenfor fornuftig område, sett til 0
  if (raw <= 0 || raw >= 16383) {
    // (Kan logge en advarsel hvis ønsket)
    raw = 0;
  }

  // Sjekk om trykket hopper over terskel => indikerer et "pust"
  if (abs(raw - lastPressureSample) > breathThreshold) {
    breathCount++;
    // Oppdater siste sample for ny sammenligning
    lastPressureSample = raw;
  }

  // Hver 10. sekund beregner vi BPM og nullstiller
  unsigned long now = millis();
  if (now - breathWindowStart >= BREATH_WINDOW_MS) {
    // 10 sek gikk -> BPM = (breathCount * 60 sek) / 10 sek
    // => BPM = breathCount * 6
    breathsPerMinute = breathCount * 6.0f;

    breathCount = 0;
    breathWindowStart = now;
  }

  // Valgfritt: Fjerner spamming av trykkarray.
  // Om du vil DEBUG, kan du uncomment:
  /*
  pressureBuffer[bufferIndex++] = raw;
  if (bufferIndex >= BUFFER_SIZE) {
      bufferIndex = 0;
  }
  */
}

void PressureModule::sendPressureData() {
  // KOMMENTERT UT for å unngå spam i serieutgangen
  /*
  Serial.print("{\"pressure\": [");
  for (uint8_t i = 0; i < BUFFER_SIZE; i++) {
    Serial.print(pressureBuffer[i]);
    if (i < BUFFER_SIZE - 1) Serial.print(", ");
  }
  Serial.println("]}");
  */
}

void PressureModule::resetBreathMonitor() {
  // Nullstill tellinger
  lastPressureSample = analogRead(PRESSURE_SENSOR_PIN);
  breathCount = 0;
  breathsPerMinute = 0;
  breathWindowStart = millis();
}

float PressureModule::getBreathRate() {
  // Returner sist beregnet BPM
  return breathsPerMinute;
}
