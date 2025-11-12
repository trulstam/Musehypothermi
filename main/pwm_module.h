#ifndef PWM_MODULE_H
#define PWM_MODULE_H

#include <stdint.h>

// Lavnivå-API for høyfrekvent PWM på Arduino UNO R4 (Renesas RA4M1, GPT0B →
// Arduino D6). Implementasjonen bygger nå på Arduino-kjernens Renesas PWM-
// driver (pwm.h / PwmOut) i stedet for direkte registermanipulasjon, men
// grensesnittet er uendret slik at PID- og GUI-lag kan fortsette å bruke
// modulen transparent.
// Gyldige frekvenser er 1 Hz – 24 MHz (GTPR ≥ 1).
bool pwmBegin(uint32_t targetHz); // Returnerer false dersom parameter er ugyldig
void pwmSetDuty01(float duty01);  // Setter duty i området 0.0–1.0
void pwmSelfTest();               // Kjører enkel 25/50/75/0 %-sekvens for maskinvaretest
void pwmDebugDump();              // Logger registerstatus til Serial for feilsøking
void pwmStop();                   // Stopper GPT0 og setter duty til 0

class PWMModule {
public:
    PWMModule();
    void begin();                // Initierer GPT0 med standard 1 kHz PWM (midlertidig)
    void setDutyCycle(int duty); // 0–2399 (maps til 0.0–1.0 duty)
    void stopPWM();              // Setter duty til 0 og stopper generatoren
};

#endif
