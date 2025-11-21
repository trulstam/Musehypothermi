#include <cassert>
#include <chrono>
#include <thread>
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

    ProfileManager::ProfileStep steps[3] = {
        {0, 30.0f},
        {50, 32.0f},
        {100, 28.0f}
    };

    assert(profileManager.loadProfile(steps, 3));
    bool started = profileManager.start();
    assert(started);
    assert(profileManager.isActive());

    for (int i = 0; i < 15; ++i) {
        profileManager.update();
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    // Profile should have completed and reset
    assert(!profileManager.isActive());
    assert(profileManager.getCurrentStep() == 0);

    // Panic/failsafe block profile start
    triggerPanic("unit_test_panic");
    assert(!profileManager.start());
    clearPanic();

    assert(profileManager.loadProfile(steps, 3));
    started = profileManager.start();
    assert(started);
    triggerFailsafe("unit_test_failsafe");
    profileManager.update();
    assert(!profileManager.isActive());
    assert(profileManager.getCurrentStep() == 0);

    std::cout << "test_profile passed" << std::endl;
    return 0;
}
