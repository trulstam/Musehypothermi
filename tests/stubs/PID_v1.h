#pragma once

#include <algorithm>

#define DIRECT 0
#define MANUAL 0
#define AUTOMATIC 1

class PID {
public:
    PID(double* input, double* output, double* setpoint, double, double, double, int)
        : input_(input), output_(output), setpoint_(setpoint), outMin_(-255.0), outMax_(255.0) {}

    void SetSampleTime(int) {}
    void SetMode(int) {}
    void SetTunings(double, double, double) {}

    void SetOutputLimits(double min, double max) {
        outMin_ = min;
        outMax_ = max;
        clampOutput();
    }

    void Compute() {
        if (!output_) {
            return;
        }
        // Simple stub: drive towards the maximum magnitude respecting limits.
        double desired = (*setpoint_ >= *input_) ? outMax_ : outMin_;
        *output_ = desired;
        clampOutput();
    }

private:
    void clampOutput() {
        if (!output_) return;
        if (*output_ > outMax_) {
            *output_ = outMax_;
        } else if (*output_ < outMin_) {
            *output_ = outMin_;
        }
    }

    double* input_;
    double* output_;
    double* setpoint_;
    double outMin_;
    double outMax_;
};

