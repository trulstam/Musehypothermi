#pragma once
#include <cmath>

#ifndef SIMULATION_MODE
#define SIMULATION_MODE 0
#endif

#if SIMULATION_MODE
#include "../simulation/host_arduino_stubs.h"

#define AUTOMATIC 1
#define MANUAL 0
#define DIRECT 0
#define REVERSE 1

class PID {
public:
    PID(double* input, double* output, double* setpoint,
        double Kp, double Ki, double Kd, int direction = DIRECT)
        : myInput(input), myOutput(output), mySetpoint(setpoint),
          kp(Kp), ki(Ki), kd(Kd), mode(MANUAL), lastTime(millis()) {}

    void SetTunings(double Kp, double Ki, double Kd) {
        kp = Kp; ki = Ki; kd = Kd;
    }

    void SetSampleTime(int) {}
    void SetOutputLimits(double, double) {}

    void SetMode(int newMode) { mode = newMode; }

    bool Compute() {
        if (mode == MANUAL) { return false; }
        unsigned long now = millis();
        double timeChange = (now - lastTime) / 1000.0;
        if (timeChange <= 0) { timeChange = 0.1; }
        double error = (*mySetpoint) - (*myInput);
        integral += error * timeChange;
        double derivative = (error - lastError) / timeChange;
        *myOutput = kp * error + ki * integral + kd * derivative;
        lastError = error;
        lastTime = now;
        return true;
    }

private:
    double *myInput, *myOutput, *mySetpoint;
    double kp, ki, kd;
    int mode;
    unsigned long lastTime;
    double lastError {0.0};
    double integral {0.0};
};
#endif
