#pragma once

#if SIMULATION_MODE
#include "../../simulation/host_firmware_stubs.h"

class ProfileManager {
public:
    struct ProfileStep { float time; float temp; };
    void begin() {}
    bool loadProfile(const ProfileStep*, uint8_t) { return true; }
    bool start() { active = true; return true; }
    void stop() {}
    void pause() {}
    void resume() {}
    void abortDueToSafety(const char*) { active = false; }
    bool isActive() const { return active; }
    bool isPaused() const { return false; }
    uint8_t getCurrentStep() const { return 0; }
private:
    bool active {false};
};

extern ProfileManager profileManager;
#endif
