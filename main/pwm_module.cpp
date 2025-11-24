#include "pwm_module.h"

PWMModule::PWMModule() : _pwm(D6) {}

void PWMModule::begin() {
    pinMode(D6, OUTPUT);
    _pwm.begin(20000.0f, 0.0f);
}

void PWMModule::setDutyCycle(int duty) {
    const int clampedDuty = constrain(duty, 0, 2399);
    lastDutyCycle = clampedDuty;

    const float dutyPercent = (static_cast<float>(clampedDuty) * 100.0f) / 2399.0f;
    lastDutyPercent = constrain(dutyPercent, 0.0f, 100.0f);

    _pwm.pulse_perc(lastDutyPercent);
}

void PWMModule::stopPWM() {
    lastDutyCycle = 0;
    lastDutyPercent = 0.0f;
    _pwm.pulse_perc(0.0f);
}
