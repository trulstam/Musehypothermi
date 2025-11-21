#include <cassert>
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
    sensors.setSimulatedTemps(22.0, 22.0);
    pid.begin(eeprom);
    pid.setTargetTemp(30.0f);
    pid.setOutputLimits(-60.0f, 60.0f);
    pid.start();
    pid.update(0.0);

    triggerFailsafe("unit_test_fail");
    assert(isFailsafeActive());
    pid.update(0.0);
    assert(std::fabs(pid.getOutput()) < 1e-3);
    assert(currentPwmOutput == 0);

    pid.startAsymmetricAutotune(10.0f, "heating", 1.0f);
    triggerFailsafe("second_fail");
    assert(!pid.isAutotuneActive());

    triggerPanic("unit_test_panic");
    assert(isPanicActive());
    assert(!isFailsafeActive());
    pid.update(0.0);
    assert(currentPwmOutput == 0);
    clearPanic();
    assert(!isPanicActive());

    std::cout << "test_failsafe passed" << std::endl;
    return 0;
}
