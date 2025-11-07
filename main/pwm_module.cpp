#include "pwm_module.h"
#include "Arduino.h"

namespace pwm_internal {
constexpr int kMaxDuty = 2399;
constexpr uint32_t kMinTargetHz = 1u;
constexpr uint32_t kMaxPeriodCounts = 0xFFFFFFFFu;
constexpr uint32_t GPT_CLK_HZ = 48000000u;

void pwmPinMux_P313_GPT0A() {
    // Lås opp PFS-register for å kunne endre pinnefunksjonen.
    R_PMISC->PWPR_b.B0WI = 0;
    R_PMISC->PWPR_b.PFSWE = 1;

    // Map Arduino pinne 6 (port 3, pinne 13) til GPT0 GTIOCA.
    R_PFS->PORT[3].PIN[13].PmnPFS = 0x11;

    // Lås PFS-registeret igjen.
    R_PMISC->PWPR_b.PFSWE = 0;
    R_PMISC->PWPR_b.B0WI = 1;
}

uint32_t pwmCalcPeriodCounts(uint32_t targetHz) {
    if (targetHz < kMinTargetHz) {
        targetHz = kMinTargetHz;
    }

    uint32_t period = GPT_CLK_HZ / targetHz;
    if (period > 0u) {
        period -= 1u;
    }

    if (period < 1u) {
        period = 1u;
    } else if (period > kMaxPeriodCounts) {
        period = kMaxPeriodCounts;
    }

    return period;
}
} // namespace pwm_internal

using pwm_internal::GPT_CLK_HZ;
using pwm_internal::kMaxDuty;
using pwm_internal::kMaxPeriodCounts;
using pwm_internal::kMinTargetHz;
using pwm_internal::pwmCalcPeriodCounts;
using pwm_internal::pwmPinMux_P313_GPT0A;

bool pwmBegin(uint32_t targetHz) {
    bool withinRange = (targetHz >= kMinTargetHz) && (targetHz <= GPT_CLK_HZ);
    uint32_t period_counts = pwmCalcPeriodCounts(targetHz);

    // Slå på klokke til GPT0-modulen.
    R_MSTP->MSTPCRD_b.MSTPD5 = 0;

    // Stopp teller før konfigurering og sett grunnleggende moduser.
    R_GPT0->GTCR_b.CST = 0;
    R_GPT0->GTCR = 0x0000;
    R_GPT0->GTUDDTYC = 0x0000; // Teller oppover.
    R_GPT0->GTIOR = 0x0303;    // PWM-modus på GTIOCA.

    // Konfigurer pinne 6 til periferi-funksjonen GPT0A.
    pwmPinMux_P313_GPT0A();

    // Sett periode og start med 0 % duty.
    R_GPT0->GTPR = period_counts;
    R_GPT0->GTCNT = 0;         // Nullstill tellerverdien.
    R_GPT0->GTCCR[0] = 0;

    // Start GPT0-telleren.
    R_GPT0->GTCR_b.CST = 1;

    return withinRange;
}

void pwmSetDuty01(float duty01) {
    if (duty01 < 0.0f) {
        duty01 = 0.0f;
    } else if (duty01 > 1.0f) {
        duty01 = 1.0f;
    }

    uint32_t period = R_GPT0->GTPR;
    double scaled = static_cast<double>(duty01) * static_cast<double>(period);
    uint32_t cc = static_cast<uint32_t>(scaled);
    if (cc > period) {
        cc = period;
    }

    R_GPT0->GTCCR[0] = cc;
}

void pwmStop() {
    R_GPT0->GTCCR[0] = 0;
    R_GPT0->GTCR_b.CST = 0;
}

PWMModule::PWMModule() {}

void PWMModule::begin() {
    pwmBegin(20000u); // Standard 20 kHz PWM.
}

void PWMModule::setDutyCycle(int duty) {
    if (duty <= 0) {
        pwmSetDuty01(0.0f);
        return;
    }

    if (duty >= kMaxDuty) {
        pwmSetDuty01(1.0f);
        return;
    }

    double duty01 = static_cast<double>(duty) / static_cast<double>(kMaxDuty);
    pwmSetDuty01(static_cast<float>(duty01));
}

void PWMModule::stopPWM() {
    pwmStop();
}
