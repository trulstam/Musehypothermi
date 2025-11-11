#ifndef PWM_MODULE_H
#define PWM_MODULE_H

#include <stdint.h>

// Lavnivå-API for høyfrekvent PWM på Arduino UNO R4 (Renesas RA4M1, GPT0B →
// Arduino D6). Frekvens og duty styres direkte via GPT0-registrene uten bruk av
// Arduino-bibliotekenes analogWrite().
// Gyldige frekvenser er 1 Hz – 24 MHz (GTPR ≥ 1).
bool pwmBegin(uint32_t targetHz); // Returnerer false dersom parameter er ugyldig
void pwmSetDuty01(float duty01);  // Setter duty i området 0.0–1.0
void pwmDebugDump();              // Logger registerstatus til Serial for feilsøking
void pwmStop();                   // Stopper GPT0 og setter duty til 0

class PWMModule {
public:
    PWMModule();
    void begin();                // Initierer GPT0 med standard 20 kHz PWM
    void setDutyCycle(int duty); // 0–2399 (maps til 0.0–1.0 duty)
    void stopPWM();              // Setter duty til 0 og stopper generatoren
};

#endif
