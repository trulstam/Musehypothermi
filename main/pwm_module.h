#ifndef PWM_MODULE_H
#define PWM_MODULE_H

#include <stdint.h>
#include <Arduino.h>
#include "pwm.h"

class PWMModule {
public:
    PWMModule();
    void begin();               // Init: configure pin and start PWM
    void setDutyCycle(int duty); // 0–2399 duty counts mapped to %
    void stopPWM();             // Sets duty to 0%

    // Host/test visibility for latest duty command
    int getLastDutyCycle() const { return lastDutyCycle; }
    float getLastDutyPercent() const { return lastDutyPercent; }

private:
    PwmOut _pwm;
    int lastDutyCycle {0};
    float lastDutyPercent {0.0f};
};

#endif
