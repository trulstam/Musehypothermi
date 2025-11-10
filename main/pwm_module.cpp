#include "pwm_module.h"
#include "Arduino.h"

namespace pwm_internal {
constexpr uint32_t kDefaultPeriodCounts = 2399u;
constexpr uint32_t kMinTargetHz = 1u;
constexpr uint32_t GPT_CLK_HZ = 48000000u;
constexpr uint32_t kMaxTargetHz = GPT_CLK_HZ / 2u; // Med GTPR ≥ 1 gir dette maksimal praktisk frekvens.
constexpr uint32_t kMaxPeriodCounts = 0xFFFFFFFFu;

volatile uint32_t g_lastPeriodCounts = kDefaultPeriodCounts;

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
    } else if (targetHz > kMaxTargetHz) {
        targetHz = kMaxTargetHz;
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

bool pwmBegin(uint32_t targetHz) {
    bool withinRange = (targetHz >= pwm_internal::kMinTargetHz) &&
                       (targetHz <= pwm_internal::kMaxTargetHz);
    uint32_t period_counts = pwm_internal::pwmCalcPeriodCounts(targetHz);

    // 1) Stopp teller og aktiver modul
    R_MSTP->MSTPCRD_b.MSTPD5 = 0;   // Enable GPT0
    R_GPT0->GTCR_b.CST = 0;
    R_GPT0->GTCR = 0x0000;
    // Configure automatic counter clear on GTPR compare so the period register
    // defines the PWM cycle length. CCLR resides in bits [6:4] of GTCR; value 0b001
    // selects "clear on GTPR compare" without starting the counter (CST remains 0).
    R_GPT0->GTCR = (R_GPT0->GTCR & static_cast<uint16_t>(~0x0070u)) |
                   static_cast<uint16_t>(0x0010u);
    R_GPT0->GTUDDTYC = 0x0000;      // Count up

    // 2) Pin-mux for P313 -> GPT0A (pin 6)
    pwm_internal::pwmPinMux_P313_GPT0A();

    // 3) Sett GTIOR for "set ved periodestart, clear ved match" på A-kanalen
    R_GPT0->GTIOR = 0xA500;

    // 4) Periode og duty = 0%
    R_GPT0->GTPR = period_counts;   // (period-1)
    R_GPT0->GTCNT = 0;
    R_GPT0->GTCCR[0] = 0;           // start med 0% duty (lav hele perioden)
    pwm_internal::g_lastPeriodCounts = period_counts;

    // 5) Start teller
    R_GPT0->GTCR_b.CST = 1;

    return withinRange;
}

void pwmSetDuty01(float duty01) {
    if (duty01 < 0.0f) {
        duty01 = 0.0f;
    } else if (duty01 > 1.0f) {
        duty01 = 1.0f;
    }

    uint32_t period = static_cast<uint32_t>(R_GPT0->GTPR) + 1u;
    uint32_t cc = static_cast<uint32_t>(static_cast<double>(duty01) *
                                        static_cast<double>(period));
    if (cc > 0u) {
        cc -= 1u;
    }

    if (period == 0u) {
        cc = 0u;
    }

    R_GPT0->GTCCR[0] = cc;
}

void pwmStop() {
    R_GPT0->GTCCR[0] = 0;
    R_GPT0->GTCR_b.CST = 0;
}

void pwmDebugDump() {
    Serial.println("=== GPT0 DEBUG ===");
    Serial.print("GTCR.CST=");   Serial.println(R_GPT0->GTCR_b.CST);
    Serial.print("GTPR=");       Serial.println(static_cast<uint32_t>(R_GPT0->GTPR));
    Serial.print("GTCNT=");      Serial.println(static_cast<uint32_t>(R_GPT0->GTCNT));
    Serial.print("GTCCR[0]=");   Serial.println(static_cast<uint32_t>(R_GPT0->GTCCR[0]));
    Serial.print("GTIOR=0x");    Serial.println(static_cast<uint32_t>(R_GPT0->GTIOR), HEX);

    R_PMISC->PWPR_b.B0WI = 0;
    R_PMISC->PWPR_b.PFSWE = 1;
    uint32_t pfs = R_PFS->PORT[3].PIN[13].PmnPFS;
    R_PMISC->PWPR_b.PFSWE = 0;
    R_PMISC->PWPR_b.B0WI = 1;
    Serial.print("P313 PmnPFS=0x"); Serial.println(pfs, HEX);
}

PWMModule::PWMModule() {}

void PWMModule::begin() {
    pwmBegin(20000u); // Standard 20 kHz PWM.
    pwmDebugDump();
}

void PWMModule::setDutyCycle(int duty) {
    if (duty <= 0) {
        pwmSetDuty01(0.0f);
        return;
    }

    uint32_t maxDuty = static_cast<uint32_t>(R_GPT0->GTPR);
    if (maxDuty == 0u) {
        maxDuty = pwm_internal::g_lastPeriodCounts;
    }

    if (duty >= static_cast<int>(maxDuty)) {
        pwmSetDuty01(1.0f);
        return;
    }

    double duty01 = static_cast<double>(duty) /
                    static_cast<double>(maxDuty);
    pwmSetDuty01(static_cast<float>(duty01));
}

void PWMModule::stopPWM() {
    pwmStop();
}
