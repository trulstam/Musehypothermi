#include "pwm_module.h"

PWMModule::PWMModule() : _pwm(D6) {}

void PWMModule::begin() {
    pinMode(D6, OUTPUT);
    _pwm.begin(20000.0f, 0.0f);
}

void PWMModule::setDutyCycle(int duty) {
    if (duty > 2399) {
        duty = 2399;
    } else if (duty < 0) {
        duty = 0;
    }

    lastDutyCycle = duty;

    float dutyPercent = static_cast<float>(duty) * 100.0f / 2399.0f;
    if (dutyPercent > 100.0f) {
        dutyPercent = 100.0f;
    } else if (dutyPercent < 0.0f) {
        dutyPercent = 0.0f;
    }

    _pwm.pulse_perc(dutyPercent);
}

void PWMModule::stopPWM() {
    lastDutyCycle = 0;
    _pwm.pulse_perc(0.0f);
}
