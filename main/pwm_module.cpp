#include "pwm_module.h"
#include "Arduino.h"

namespace pwm_internal {
constexpr int kMaxDuty = 2399;
constexpr uint32_t kMinTargetHz = 1u;
constexpr uint32_t GPT_CLK_HZ = 48000000u;
constexpr uint32_t kMaxTargetHz = GPT_CLK_HZ / 2u; // Med GTPR ≥ 1 gir dette maksimal praktisk frekvens.
constexpr uint32_t kMaxPeriodCounts = 0xFFFFFFFFu;

// GTIOR består av to 8-bits felt (GTIOCA i de øverste 8 bitene og GTIOCB i
// de nederste 8). Feltoppsettet er (MSB→LSB):
//   [7:6] OADF  – hvordan utgangen reagerer på compare-match (00=hold, 01=set,
//                  10=clear, 11=toggle)
//   [5]   OADTY – setter nivået ved periodens slutt (1=set, 0=clear)
//   [4]   OADFLT– standardnivå når timeren stoppes
//   [3]   OAHLD – hold (ikke brukt)
//   [2]   OAD   – output disable
//   [1]   OAE   – output enable
//   [0]   OASF  – nivå når timeren stoppes
constexpr uint8_t kGtioaClearOnMatch = 0x80;     // OADF=10 → clear ved match
constexpr uint8_t kGtioaSetOnPeriodEnd = 0x20;   // OADTY=1 → set ved overflow
constexpr uint8_t kGtioaDefaultLow = 0x00;       // OADFLT=0 → lav når stoppet
constexpr uint8_t kGtioaOutputEnable = 0x02;     // OAE=1
constexpr uint8_t kGtioaStopLevelLow = 0x00;     // OASF=0
constexpr uint8_t kGtioaActiveHighPwm =
        kGtioaClearOnMatch | kGtioaSetOnPeriodEnd | kGtioaDefaultLow |
        kGtioaOutputEnable | kGtioaStopLevelLow;

constexpr uint8_t kGtiobDisabled = 0x00;         // Kanal B er ikke i bruk.

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

    // Slå på klokke til GPT0-modulen.
    R_MSTP->MSTPCRD_b.MSTPD5 = 0;

    // Stopp teller før konfigurering og sett grunnleggende moduser.
    R_GPT0->GTCR_b.CST = 0;
    R_GPT0->GTCR = 0x0000;
    R_GPT0->GTUDDTYC = 0x0000; // Teller oppover.
    uint16_t gtiorValue = (static_cast<uint16_t>(pwm_internal::kGtioaActiveHighPwm)
                           << 8) |
                          pwm_internal::kGtiobDisabled;
    R_GPT0->GTIOR = gtiorValue;

    // Konfigurer pinne 6 til periferi-funksjonen GPT0A.
    pwm_internal::pwmPinMux_P313_GPT0A();

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

    if (duty >= pwm_internal::kMaxDuty) {
        pwmSetDuty01(1.0f);
        return;
    }

    double duty01 = static_cast<double>(duty) /
                    static_cast<double>(pwm_internal::kMaxDuty);
    pwmSetDuty01(static_cast<float>(duty01));
}

void PWMModule::stopPWM() {
    pwmStop();
}
