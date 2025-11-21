#pragma once
#include "../host_sim/host_firmware_stubs.h"

class PIDModule {
public:
    PIDModule() { pid.SetMode(MANUAL); }
    void setTarget(double target) { Setpoint = target; pid.SetMode(AUTOMATIC); }
    double compute(double currentTemp) {
        Input = currentTemp;
        pid.Compute();
        return Output;
    }
private:
    double Input {0.0};
    double Output {0.0};
    double Setpoint {0.0};
    PID pid {&Input, &Output, &Setpoint, 2.0, 0.5, 1.0, DIRECT};
};
