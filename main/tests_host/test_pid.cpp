#include <cassert>
#include <cmath>
#include <iostream>
#include "pid_module_asymmetric.h"
#include "sensor_module.h"
#include "pressure_module.h"
#include "profile_manager.h"
#include "task_scheduler.h"
#include "comm_api.h"

AsymmetricPIDModule pid;
SensorModule sensors;
PressureModule pressure;
EEPROMManager eeprom;
CommAPI comm(Serial);

int main() {
    sensors.setSimulatedTemps(25.0, 25.0);
    pid.begin(eeprom);
    pid.setTargetTemp(30.0f);
    pid.setOutputLimits(-40.0f, 40.0f);

    // Run a few iterations and confirm output stays within bounds
    for (int i = 0; i < 250; ++i) {
        sensors.setSimulatedTemps(25.0 + 0.01 * i, 25.0);
        pid.update(0.0);
        double output = pid.getOutput();
        assert(output <= 40.0 + 1e-3);
        assert(output >= -40.0 - 1e-3);
    }

    // Stopping the controller zeros outputs and PWM
    pid.stop();
    assert(std::fabs(pid.getOutput()) < 1e-3);
    assert(currentPwmOutput == 0);

    // Autotune shouldn't drive beyond limits and can be aborted cleanly
    pid.startAsymmetricAutotune(15.0f, "heating", 1.0f);
    pid.update(0.0);
    assert(pid.isAutotuneActive());
    pid.abortAutotune();
    pid.ensureOutputsOff();
    assert(std::fabs(pid.getOutput()) < 1e-3);

    // Equilibrium compensation scales output when valid
    pid.setUseEquilibriumCompensation(true);
#ifdef HOST_BUILD
    pid.setEquilibriumStateForTest(29.0, true, false);
#endif
    pid.setTargetTemp(32.0f);
    sensors.setSimulatedTemps(20.0, 20.0);
    pid.setOutputLimits(-50.0f, 50.0f);
    pid.update(0.0);
    assert(pid.getOutput() <= 50.0);

    std::cout << "test_pid passed" << std::endl;
    return 0;
}
