#include "pwm_module.h"
#include "Arduino.h"

PWMModule::PWMModule() {}

namespace {
constexpr uint8_t kPwmPin = 6;
constexpr int kMaxDuty = 2399;

uint8_t scaleDuty(int duty) {
    if (duty <= 0) {
        return 0;
    }
    if (duty >= kMaxDuty) {
        return 255;
    }
    // Runde til nærmeste heltall i 0–255 området.
    return static_cast<uint8_t>((static_cast<long>(duty) * 255 + kMaxDuty / 2) / kMaxDuty);
}
} // namespace

void PWMModule::begin() {
    pinMode(kPwmPin, OUTPUT);
    analogWrite(kPwmPin, 0);  // Starter med 0 % duty-cycle på standardtimeren.
}

void PWMModule::setDutyCycle(int duty) {
    analogWrite(kPwmPin, scaleDuty(duty));
}

void PWMModule::stopPWM() {
    analogWrite(kPwmPin, 0);
}
