#include "pwm_module.h"
#include "Arduino.h"

PWMModule::PWMModule() {}

void PWMModule::begin() {
    configurePin6();
    enableGPT0();
}

void PWMModule::configurePin6() {
    constexpr uint8_t kPwmPin = 6;

    // Sørg for at portkontrolleren kjenner pinnen som utgang før den
    // overlates til GPT0 – ellers blir den liggende som en vanlig
    // digital-pin som default dras høy av intern pull-up.
    pinMode(kPwmPin, OUTPUT);
    digitalWrite(kPwmPin, LOW);

    R_PMISC->PWPR_b.B0WI = 0;
    R_PMISC->PWPR_b.PFSWE = 1;

    // Pin 6 (P313) til GPT0 GTIOCA: sett funksjonsvelgeren (0x11)
    // og sørg for at PMR-biten er aktivert slik at periferien tar eierskap
    // til pinnen. Vi bevarer øvrige flagg i tilfelle oppstartskoden har
    // konfigurert pull-ups el.l.
    volatile uint32_t &p313_pfs = R_PFS->PORT[3].PIN[13].PmnPFS;
    p313_pfs = (p313_pfs & ~0x3Fu) | 0x11u;
    p313_pfs |= (1u << 6);  // PMR = 1 → peripheral mode

    R_PMISC->PWPR_b.PFSWE = 0;
    R_PMISC->PWPR_b.B0WI = 1;

}

void PWMModule::enableGPT0() {
    R_MSTP->MSTPCRD_b.MSTPD5 = 0;  // Enable GPT0
    R_GPT0->GTCR = 0x0000;         // Stop timer
    R_GPT0->GTUDDTYC = 0x0000;     // Count up
    R_GPT0->GTIOR = 0x0303;        // PWM mode

    R_GPT0->GTPR = 2399;           // 20kHz period (48MHz / 20kHz - 1)
    R_GPT0->GTCCR[0] = 0;          // Start with 0% duty

    R_GPT0->GTCR_b.CST = 1;        // Start counter
}

void PWMModule::setDutyCycle(int duty) {
    if (duty > 2399) duty = 2399;
    if (duty < 0) duty = 0;
    R_GPT0->GTCCR[0] = duty;
}

void PWMModule::stopPWM() {
    R_GPT0->GTCCR[0] = 0;          // ← nullstill duty til 0
    R_GPT0->GTCR_b.CST = 0;        // ← stopp teller
}
