#pragma once
#include "host_arduino_stubs.h"
#include "host_pid_v1_stub.h"

class EEPROMManager {
public:
    void loadPIDParams(float &kp, float &ki, float &kd) { kp = 2.0f; ki = 0.5f; kd = 1.0f; }
    void savePIDParams(float, float, float) {}
    void loadTargetTemp(float &target) { target = 37.0f; }
    void saveTargetTemp(float) {}
    void loadMaxOutput(float &value) { value = 50.0f; }
    void saveMaxOutput(float) {}
    void loadProfile(uint8_t&, uint8_t&, uint8_t&) {}
};

class PWMModule {
public:
    void begin() {}
    void setPWM(int) {}
    void stopPWM() {}
};

class SensorModule {
public:
    double getCoolingPlateTemp() { return simulatedTemp; }
    double getAnalProbeTemp() { return simulatedTemp; }
    double getPressureCmH2O() { return 0.0; }
    double simulatedTemp {25.0};
};

class PressureModule {
public:
    float getLastPressure() const { return 0.0f; }
};

class TaskScheduler {
public:
    void addTask(const char*, unsigned long, void (*)()) {}
    void run() {}
};

inline void triggerFailsafe(const char*) {}
inline void clearFailsafe() {}
inline bool isFailsafeActive() { return false; }
inline const char* getFailsafeReason() { return ""; }
inline void triggerPanic(const char*) {}
inline void clearPanic() {}
inline bool isPanicActive() { return false; }
inline const char* getPanicReason() { return ""; }

class CommAPI {
public:
    void sendEvent(const String& msg) { std::printf("EVENT: %s\n", msg.c_str()); }
    void sendStatus() {}
};

static CommAPI comm;
