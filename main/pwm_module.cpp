#include "pwm_module.h"

#include <Arduino.h>
#include <pwm.h>

namespace pwm_internal {
constexpr uint32_t kGptClockHz = 48000000u;
constexpr uint32_t kMinTargetHz = 1u;
constexpr uint32_t kMaxTargetHz = kGptClockHz / 2u; // tilsvarer GTPR ≥ 1
constexpr float kDutyZeroEpsilon = 1e-6f;

PwmOut g_pwmChannel(PIN_D6);
uint32_t g_lastTargetHz = 20000u;
uint32_t g_lastPeriodCounts = (kGptClockHz / 20000u) - 1u; // 2399 ved 20 kHz
float g_lastDuty01 = 0.0f;
bool g_initialized = false;

uint32_t pwmCalcPeriodCounts(uint32_t targetHz) {
    if (targetHz < kMinTargetHz) {
        targetHz = kMinTargetHz;
    } else if (targetHz > kMaxTargetHz) {
        targetHz = kMaxTargetHz;
    }

    uint32_t period = kGptClockHz / targetHz;
    if (period > 0u) {
        period -= 1u;
    }

    if (period < 1u) {
        period = 1u;
    }

    return period;
}

float pwmCountsToHz(uint32_t periodCounts) {
    return static_cast<float>(kGptClockHz) /
           static_cast<float>(periodCounts + 1u);
}

void pwmApplyDuty(float duty01) {
    g_pwmChannel.pulse_perc(duty01 * 100.0f);
    g_lastDuty01 = duty01;
}
} // namespace pwm_internal

bool pwmBegin(uint32_t targetHz) {
    bool withinRange = (targetHz >= pwm_internal::kMinTargetHz) &&
                       (targetHz <= pwm_internal::kMaxTargetHz);

    uint32_t periodCounts = pwm_internal::pwmCalcPeriodCounts(targetHz);
    float actualHz = pwm_internal::pwmCountsToHz(periodCounts);

    pinMode(PIN_D6, OUTPUT);
    digitalWrite(PIN_D6, LOW);

    pwm_internal::g_pwmChannel.begin(actualHz, 0.0f);

    pwm_internal::g_lastTargetHz = static_cast<uint32_t>(actualHz + 0.5f);
    pwm_internal::g_lastPeriodCounts = periodCounts;
    pwm_internal::g_lastDuty01 = 0.0f;
    pwm_internal::g_initialized = true;

    // 6) Overlat pinnen til GPT0B nå som timeren allerede går i lav tilstand.
    pwm_internal::pwmPinMux_P106_GPT0B();

    return withinRange;
}

void pwmSetDuty01(float duty01) {
    if (!pwm_internal::g_initialized) {
        return;
    }

    if (duty01 < 0.0f) {
        duty01 = 0.0f;
    } else if (duty01 > 1.0f) {
        duty01 = 1.0f;
    }

    if (duty01 <= pwm_internal::kDutyZeroEpsilon) {
        pwm_internal::pwmApplyDuty(0.0f);
        return;
    }

    pwm_internal::pwmApplyDuty(duty01);
}

void pwmStop() {
    if (!pwm_internal::g_initialized) {
        return;
    }

    pwm_internal::pwmApplyDuty(0.0f);
}

void pwmSelfTest() {
    if (!pwm_internal::g_initialized) {
        return;
    }

    constexpr float kSteps[] = {0.25f, 0.50f, 0.75f, 0.00f};
    for (float duty : kSteps) {
        pwmSetDuty01(duty);
        delay(300);
    }
}

void pwmDebugDump() {
    Serial.println("=== PWM DEBUG ===");
    Serial.print("Target Hz (rounded)=");
    Serial.println(pwm_internal::g_lastTargetHz);
    Serial.print("Actual Hz=");
    Serial.println(pwm_internal::pwmCountsToHz(pwm_internal::g_lastPeriodCounts), 2);
    Serial.print("Period counts=");
    Serial.println(pwm_internal::g_lastPeriodCounts);
    Serial.print("Duty 0-1=");
    Serial.println(pwm_internal::g_lastDuty01, 6);
    Serial.print("Duty %=");
    Serial.println(pwm_internal::g_lastDuty01 * 100.0f, 2);
    Serial.print("Initialized=");
    Serial.println(pwm_internal::g_initialized ? 1 : 0);
    Serial.print("PIN_D6 state=");
    Serial.println(digitalRead(PIN_D6));
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
    pwmBegin(20000u);
    pwmDebugDump();
    pwmSelfTest(); // TEMPORARY: remove after validation
}

void PWMModule::setDutyCycle(int duty) {
    if (duty <= 0) {
        pwmSetDuty01(0.0f);
        return;
    }

    uint32_t maxDuty = pwm_internal::g_lastPeriodCounts;
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

