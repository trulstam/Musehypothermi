#include <cstdio>
#include "Arduino_host.h"
#include "host_firmware_stubs.h"
#include "../host_stubs/pid_module.h"
#include "../host_stubs/profile_manager.h"
#include "../host_stubs/comm_api.h"
#include "../host_stubs/sensor_module.h"
#include "../host_stubs/pressure_module.h"

SensorModule sensors;
PressureModule pressure;
ProfileManager profileManager;

int main() {
    PIDModule pid;
    double plateTemp = 25.0;
    pid.setTarget(37.0);

    for (int t = 0; t < 300; t++) {
        double output = pid.compute(plateTemp);
        plateTemp += 0.05 * output - 0.01 * (plateTemp - 25.0);
        std::printf("%d %.3f %.3f\n", t, plateTemp, output);
    }
    return 0;
}
