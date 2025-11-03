#include <algorithm>
#include <cassert>
#include <cmath>
#include <string>

#include "pid_module.h"

unsigned long __mockMillis = 0;

void setMockMillis(unsigned long value) { __mockMillis = value; }
void advanceMockMillis(unsigned long delta) { __mockMillis += delta; }

SensorModule sensors;
CommAPI comm;
int currentPwmOutput = 0;

bool failsafeActive = false;

void triggerFailsafe(const char*) { failsafeActive = true; }
void clearFailsafe() { failsafeActive = false; }
bool isFailsafeActive() { return failsafeActive; }

int main() {
    PIDModule pid;
    EEPROMManager eeprom;
    eeprom.setInitialMaxOutput(60.0f);

    setMockMillis(0);
    sensors.setCoolingPlateTemp(30.0);

    pid.begin(eeprom);

    assert(std::fabs(pid.getMaxOutputPercent() - 20.0f) < 1e-3f);

    bool clampEventFound = false;
    for (const auto& evt : comm.events) {
        if (evt.find("Startup max output limited") != std::string::npos) {
            clampEventFound = true;
            break;
        }
    }
    assert(clampEventFound);

    pid.start();

    assert(std::fabs(pid.getPersistedMaxOutputPercent() - 60.0f) < 1e-3f);

    setMockMillis(61000);
    pid.update(30.0);

    bool releaseEventFound = false;
    for (const auto& evt : comm.events) {
        if (evt.find("Startup max output clamp released") != std::string::npos) {
            releaseEventFound = true;
            break;
        }
    }
    assert(releaseEventFound);

    assert(std::fabs(pid.getMaxOutputPercent() - 60.0f) < 1e-3f);
    assert(std::fabs(pid.getPersistedMaxOutputPercent() - 60.0f) < 1e-3f);

    auto statusIt = comm.statuses.find("pid_output_limit");
    assert(statusIt != comm.statuses.end());
    assert(std::fabs(statusIt->second - 60.0) < 1e-3);

    double percent = (pid.getOutput() / static_cast<double>(MAX_PWM)) * 100.0;
    assert(percent > 20.0 + 1e-3);

    return 0;
}

