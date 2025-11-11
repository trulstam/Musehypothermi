#include "pwm_module.h"
#include "Arduino.h"

namespace pwm_internal {
constexpr uint32_t kDefaultPeriodCounts = 2399u;
constexpr uint32_t kMinTargetHz = 1u;
constexpr uint32_t GPT_CLK_HZ = 48000000u;
constexpr uint32_t kMaxTargetHz = GPT_CLK_HZ / 2u; // Med GTPR ≥ 1 gir dette maksimal praktisk frekvens.
constexpr uint32_t kMaxPeriodCounts = 0xFFFFFFFFu;

constexpr uint8_t kPolarityMode = 0; // 0=Set@start,Clear@match; 1=Clear@start,Set@match

constexpr uint16_t kGTIORB_SetAtOverflowClearOnCompare = 0x00A5u;  // active-high PWM profile
constexpr uint16_t kGTIORB_ClearAtOverflowSetOnCompare = 0x005Au;  // active-low PWM profile
constexpr uint16_t kGTIORB_OutputIdleLowMask = 0xFFDFu;

volatile uint32_t g_lastPeriodCounts = kDefaultPeriodCounts;
volatile bool g_outputEnabled = false;

uint16_t pwmSelectPolarityPattern() {
    return (kPolarityMode == 0)
               ? kGTIORB_SetAtOverflowClearOnCompare
               : kGTIORB_ClearAtOverflowSetOnCompare;
}

uint16_t pwmSelectDisabledPattern() {
    uint16_t base = pwmSelectPolarityPattern();
    base &= kGTIORB_OutputIdleLowMask; // Force idle low when disabled.
    base &= static_cast<uint16_t>(0xFFFEu);
    return base;
}

void pwmApplyGtiobPattern(uint16_t pattern) {
    R_GPT0->GTIOR = (R_GPT0->GTIOR & 0xFF00u) | pattern;
}

void pwmDisableOutput() {
    pwmApplyGtiobPattern(pwmSelectDisabledPattern());
    g_outputEnabled = false;
}

void pwmEnableOutput() {
    pwmApplyGtiobPattern(pwmSelectPolarityPattern());
    g_outputEnabled = true;
}

static inline void predrive_D6_low_gpio() {
    pinMode(6, OUTPUT);
    digitalWrite(6, LOW);
}

void pwmPinMux_P106_GPT0B() {
    // Lås opp PFS-register for å kunne endre pinnefunksjonen.
    R_PMISC->PWPR_b.B0WI = 0;
    R_PMISC->PWPR_b.PFSWE = 1;

    // Map Arduino pinne 6 (port 1, pinne 6) til GPT0 GTIOCB.
    R_PFS->PORT[1].PIN[6].PmnPFS = 0x12;

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
    // defines the PWM cycle length. CCLR resides in bits [6:4] of GTCR; value 0b100
    // selects "clear on GTPR compare" without starting the counter (CST remains 0).
    R_GPT0->GTCR = (R_GPT0->GTCR & static_cast<uint32_t>(~0x0070u)) |
                   static_cast<uint32_t>(0x0040u);
    R_GPT0->GTUDDTYC = 0x0000;      // Count up

    // 2) Hold pinnen lav som GPIO før vi gir kontroll til periferi.
    pwm_internal::predrive_D6_low_gpio();

    // 3) Konfigurer GTIOR for valgt polaritet og deaktiver utgangen logisk
    // før vi starter telleren.
    pwm_internal::pwmApplyGtiobPattern(pwm_internal::pwmSelectPolarityPattern());
    pwm_internal::pwmDisableOutput();

    // 4) Periode og duty = 0%
    R_GPT0->GTPR = period_counts;   // (period-1)
    R_GPT0->GTCNT = 0;
    R_GPT0->GTCCR[1] = 1;           // bruk 1-takt compare for effektivt 0 % duty
    pwm_internal::g_lastPeriodCounts = period_counts;

    // 5) Start teller
    R_GPT0->GTCR_b.CST = 1;

    // 6) Overlat pinnen til GPT0B nå som timeren allerede går i lav tilstand.
    pwm_internal::pwmPinMux_P106_GPT0B();

    return withinRange;
}

void pwmSetDuty01(float duty01) {
    if (duty01 < 0.0f) {
        duty01 = 0.0f;
    } else if (duty01 > 1.0f) {
        duty01 = 1.0f;
    }

    uint32_t period = static_cast<uint32_t>(R_GPT0->GTPR) + 1u;

    if (duty01 <= 1e-6f) {
        // Hold compare på 1 for å sikre at "clear on compare" skjer tidlig i perioden
        // og dermed gir en lav utgang for 0 % duty.
        R_GPT0->GTCCR[1] = 1u;
        if (pwm_internal::g_outputEnabled) {
            pwm_internal::pwmDisableOutput();
        }
        return;
    }

    if (!pwm_internal::g_outputEnabled) {
        pwm_internal::pwmEnableOutput();
    }

    uint32_t cc = static_cast<uint32_t>(static_cast<double>(duty01) *
                                        static_cast<double>(period));
    if (cc > 0u) {
        cc -= 1u;
    }

    if (period == 0u) {
        cc = 0u;
    }

    R_GPT0->GTCCR[1] = cc;
}

void pwmStop() {
    R_GPT0->GTCCR[1] = 1u;
    if (pwm_internal::g_outputEnabled) {
        pwm_internal::pwmDisableOutput();
    }
    R_GPT0->GTCR_b.CST = 0;
}

static inline void pwmSetCounts(uint32_t cc) {
    R_GPT0->GTCCR[1] = cc;
}

void pwmSelfTest() {
    uint32_t period = static_cast<uint32_t>(R_GPT0->GTPR) + 1u;
    auto setPct = [&](float p) {
        if (p < 0.0f) {
            p = 0.0f;
        } else if (p > 1.0f) {
            p = 1.0f;
        }
        double scaled = static_cast<double>(p) * static_cast<double>(period);
        uint32_t cc = static_cast<uint32_t>(scaled);
        if (cc == 0u) {
            cc = 1u;
        } else {
            cc -= 1u;
        }
        pwmSetCounts(cc);
        if (pwm_internal::g_outputEnabled == false) {
            pwm_internal::pwmEnableOutput();
        }
        delay(300);
    };

    setPct(0.25f);
    setPct(0.50f);
    setPct(0.75f);
    setPct(0.00f);
    pwmSetDuty01(0.0f); // Sikre at vi avslutter i deaktivert, lav tilstand.
}

void pwmDebugDump() {
    Serial.println("=== GPT0 DEBUG ===");
    Serial.print("GTCR=0x");     Serial.println(static_cast<uint32_t>(R_GPT0->GTCR), HEX);
    Serial.print("GTCR.CST=");   Serial.println(R_GPT0->GTCR_b.CST);
    Serial.print("GTPR=");       Serial.println(static_cast<uint32_t>(R_GPT0->GTPR));
    Serial.print("GTCNT=");      Serial.println(static_cast<uint32_t>(R_GPT0->GTCNT));
    Serial.print("GTCCR[0]=");   Serial.println(static_cast<uint32_t>(R_GPT0->GTCCR[0]));
    Serial.print("GTCCR[1]=");   Serial.println(static_cast<uint32_t>(R_GPT0->GTCCR[1]));
    Serial.print("GTIOR=0x");    Serial.println(static_cast<uint32_t>(R_GPT0->GTIOR), HEX);
    Serial.print("GTIOB enabled="); Serial.println(pwm_internal::g_outputEnabled ? 1 : 0);

    R_PMISC->PWPR_b.B0WI = 0;
    R_PMISC->PWPR_b.PFSWE = 1;
    uint32_t pfs = R_PFS->PORT[1].PIN[6].PmnPFS;
    R_PMISC->PWPR_b.PFSWE = 0;
    R_PMISC->PWPR_b.B0WI = 1;
    Serial.print("P106 PmnPFS=0x"); Serial.println(pfs, HEX);
}

PWMModule::PWMModule() {}

void PWMModule::begin() {
    pwmBegin(20000u); // Standard 20 kHz PWM.
    pwmDebugDump();
    pwmSelfTest(); // TEMPORARY: remove after validation
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
